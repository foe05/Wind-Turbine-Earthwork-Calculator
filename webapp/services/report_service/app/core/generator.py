"""
Report generation utilities
"""
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from datetime import datetime
from pathlib import Path
import logging
import uuid

from .chart_generator import (
    generate_volume_chart,
    generate_multi_site_comparison_chart,
    generate_cost_comparison_chart,
    is_matplotlib_available
)
from .branding import (
    process_logo,
    process_footer_text,
    LogoValidationError,
    FooterValidationError
)
import base64

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Report generator using Jinja2 templates"""

    def __init__(self, templates_dir: str):
        """
        Initialize report generator

        Args:
            templates_dir: Path to templates directory
        """
        self.templates_dir = Path(templates_dir)
        self.env = Environment(loader=FileSystemLoader(str(self.templates_dir)))

    def generate_html(
        self,
        template_name: str,
        data: dict,
        output_path: Path
    ) -> Path:
        """
        Generate HTML report

        Args:
            template_name: Template filename (e.g., 'wka_report.html')
            data: Template data
            output_path: Output file path

        Returns:
            Path to generated HTML file
        """
        logger.info(f"Generating HTML report: {template_name}")

        # Load template
        template = self.env.get_template(template_name)

        # Add metadata
        now = datetime.now()
        data['report_date'] = now.strftime('%d.%m.%Y')
        data['report_time'] = now.strftime('%H:%M')

        # Render
        html_content = template.render(**data)

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"  ✓ HTML report generated: {output_path}")

        return output_path

    def generate_pdf(
        self,
        html_path: Path,
        output_path: Path
    ) -> Path:
        """
        Generate PDF from HTML

        Args:
            html_path: Path to HTML file
            output_path: Output PDF path

        Returns:
            Path to generated PDF file
        """
        logger.info(f"Generating PDF from HTML: {html_path}")

        # Custom CSS for PDF (optional)
        pdf_css = CSS(string='''
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-size: 12px;
            }
        ''')

        # Convert to PDF
        output_path.parent.mkdir(parents=True, exist_ok=True)

        HTML(filename=str(html_path)).write_pdf(
            target=str(output_path),
            stylesheets=[pdf_css]
        )

        logger.info(f"  ✓ PDF report generated: {output_path}")

        return output_path

    def _generate_charts(self, template: str, data: dict) -> None:
        """
        Generate charts for the report and add to data dictionary.

        Args:
            template: Template name ('wka', 'road', 'solar', 'terrain')
            data: Report data dictionary (modified in place)
        """
        if not is_matplotlib_available():
            logger.warning("matplotlib not available, skipping chart generation")
            return

        logger.info("Generating charts for report")

        try:
            if template == 'wka':
                self._generate_wka_charts(data)
            elif template == 'road':
                self._generate_road_charts(data)
            elif template == 'solar':
                self._generate_solar_charts(data)
            elif template == 'terrain':
                self._generate_terrain_charts(data)
        except Exception as e:
            logger.error(f"Error generating charts: {e}", exc_info=True)
            # Continue without charts rather than failing the entire report

    def _generate_wka_charts(self, data: dict) -> None:
        """
        Generate charts for WKA reports.

        Args:
            data: WKA report data dictionary (modified in place)
        """
        sites = data.get('sites', [])
        if not sites:
            return

        # Generate individual site volume charts
        for site in sites:
            total_cut = site.get('total_cut', 0)
            total_fill = site.get('total_fill', 0)
            site_id = site.get('id', '')

            if total_cut > 0 or total_fill > 0:
                chart_data = generate_volume_chart(
                    cut_volume=total_cut,
                    fill_volume=total_fill,
                    title=f"Erdarbeiten - WKA {site_id}",
                    dpi=150  # Lower DPI for performance
                )

                if chart_data:
                    site['volume_chart'] = chart_data
                    logger.info(f"  ✓ Volume chart generated for WKA {site_id}")

        # Generate multi-site comparison charts if multiple sites
        if len(sites) > 1:
            # Volume comparison chart
            sites_data = [
                {
                    'id': site.get('id'),
                    'total_cut': site.get('total_cut', 0),
                    'total_fill': site.get('total_fill', 0)
                }
                for site in sites
            ]

            comparison_chart = generate_multi_site_comparison_chart(
                sites_data=sites_data,
                dpi=150
            )

            if comparison_chart:
                data['volume_comparison_chart'] = comparison_chart
                logger.info("  ✓ Multi-site volume comparison chart generated")

            # Cost comparison chart
            cost_comparison_chart = generate_cost_comparison_chart(
                sites_data=[
                    {
                        'id': site.get('id'),
                        'cost_total': site.get('cost_total', 0)
                    }
                    for site in sites
                ],
                dpi=150
            )

            if cost_comparison_chart:
                data['cost_comparison_chart'] = cost_comparison_chart
                logger.info("  ✓ Multi-site cost comparison chart generated")

    def _generate_road_charts(self, data: dict) -> None:
        """
        Generate charts for road reports.

        Args:
            data: Road report data dictionary (modified in place)
        """
        road_data = data.get('road_data')
        if not road_data:
            return

        total_cut = road_data.get('total_cut', 0)
        total_fill = road_data.get('total_fill', 0)

        if total_cut > 0 or total_fill > 0:
            chart_data = generate_volume_chart(
                cut_volume=total_cut,
                fill_volume=total_fill,
                title="Straßenbau - Erdarbeiten",
                dpi=150
            )

            if chart_data:
                data['volume_chart'] = chart_data
                logger.info("  ✓ Road volume chart generated")

    def _generate_solar_charts(self, data: dict) -> None:
        """
        Generate charts for solar park reports.

        Args:
            data: Solar report data dictionary (modified in place)
        """
        solar_data = data.get('solar_data')
        if not solar_data:
            return

        total_cut = solar_data.get('total_cut', 0)
        total_fill = solar_data.get('total_fill', 0)

        if total_cut > 0 or total_fill > 0:
            chart_data = generate_volume_chart(
                cut_volume=total_cut,
                fill_volume=total_fill,
                title="Solarpark - Erdarbeiten",
                dpi=150
            )

            if chart_data:
                data['volume_chart'] = chart_data
                logger.info("  ✓ Solar park volume chart generated")

    def _generate_terrain_charts(self, data: dict) -> None:
        """
        Generate charts for terrain analysis reports.

        Args:
            data: Terrain report data dictionary (modified in place)
        """
        terrain_data = data.get('terrain_data')
        if not terrain_data:
            return

        cut_volume = terrain_data.get('cut_volume', 0)
        fill_volume = terrain_data.get('fill_volume', 0)

        if cut_volume > 0 or fill_volume > 0:
            chart_data = generate_volume_chart(
                cut_volume=cut_volume,
                fill_volume=fill_volume,
                title="Geländeanalyse - Erdarbeiten",
                dpi=150
            )

            if chart_data:
                data['volume_chart'] = chart_data
                logger.info("  ✓ Terrain analysis volume chart generated")

    def _process_branding(self, data: dict) -> None:
        """
        Process and validate branding options for the report.

        Args:
            data: Report data dictionary (modified in place)
        """
        branding = data.get('branding')
        if not branding:
            return

        logger.info("Processing branding options")

        try:
            # Process logo if provided
            logo_base64 = branding.get('logo_base64')
            if logo_base64:
                try:
                    # Validate the logo by decoding from base64 and re-encoding
                    logo_bytes = base64.b64decode(logo_base64)
                    # Validate and re-encode (process_logo validates if needed)
                    validated_logo_base64 = process_logo(logo_bytes, validate=True)
                    branding['logo_base64'] = validated_logo_base64
                    logger.info("  ✓ Logo validated and processed")
                except (base64.binascii.Error, LogoValidationError) as e:
                    logger.warning(f"  ⚠ Logo validation failed: {e}. Removing logo from report.")
                    branding['logo_base64'] = None

            # Process footer text if provided
            custom_footer = branding.get('custom_footer_text')
            if custom_footer:
                try:
                    sanitized_footer = process_footer_text(custom_footer, validate=True)
                    branding['custom_footer_text'] = sanitized_footer
                    logger.info("  ✓ Footer text validated and sanitized")
                except FooterValidationError as e:
                    logger.warning(f"  ⚠ Footer validation failed: {e}. Using default footer.")
                    branding['custom_footer_text'] = None

        except Exception as e:
            logger.error(f"Error processing branding options: {e}", exc_info=True)
            # Continue without branding rather than failing the entire report
            data['branding'] = None

    def generate_report(
        self,
        template: str,
        data: dict,
        output_format: str,
        reports_dir: Path
    ) -> tuple[Path, str]:
        """
        Generate report (HTML or PDF)

        Args:
            template: Template name ('wka', 'road', 'solar', 'terrain')
            data: Report data
            output_format: 'html' or 'pdf'
            reports_dir: Directory for reports

        Returns:
            Tuple of (file_path, report_id)
        """
        # Generate unique ID
        report_id = str(uuid.uuid4())

        # Template mapping
        template_files = {
            'wka': 'wka_report.html',
            'road': 'road_report.html',
            'solar': 'solar_report.html',
            'terrain': 'terrain_report.html'
        }

        template_file = template_files.get(template, 'wka_report.html')

        # Process branding options before rendering template
        self._process_branding(data)

        # Generate charts before rendering template
        self._generate_charts(template, data)

        # Generate HTML first
        html_path = reports_dir / f"report_{report_id}.html"
        self.generate_html(template_file, data, html_path)

        if output_format == 'pdf':
            # Convert to PDF
            pdf_path = reports_dir / f"report_{report_id}.pdf"
            self.generate_pdf(html_path, pdf_path)

            # Optionally delete HTML
            # html_path.unlink()

            return pdf_path, report_id
        else:
            return html_path, report_id
