"""
Report generation utilities
"""
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML, CSS
from datetime import datetime
from pathlib import Path
import logging
import uuid

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
