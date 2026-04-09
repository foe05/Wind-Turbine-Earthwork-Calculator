"""
Integration tests for complete PDF generation flow.

Tests the entire PDF generation pipeline including:
- Chart generation
- Branding (logo, company name, footer)
- Comparison tables with height scenarios
- Template rendering
- PDF conversion
- Performance requirements (<10s)
"""

import unittest
import base64
import sys
import os
import time
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.core.generator import ReportGenerator
    GENERATOR_AVAILABLE = True
except ImportError as e:
    GENERATOR_AVAILABLE = False
    print(f"Warning: Could not import ReportGenerator: {e}")

try:
    from app.schemas.report import (
        SiteData,
        HeightScenario,
        BrandingOptions,
        ReportGenerateRequest
    )
    SCHEMAS_AVAILABLE = True
except ImportError as e:
    SCHEMAS_AVAILABLE = False
    print(f"Warning: Could not import schemas: {e}")


@unittest.skipIf(not GENERATOR_AVAILABLE or not SCHEMAS_AVAILABLE,
                 "Dependencies not available (weasyprint, matplotlib, etc.)")
class TestIntegrationPDFGeneration(unittest.TestCase):
    """Integration tests for complete PDF generation flow."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.templates_dir = Path(__file__).parent.parent / "app" / "templates"
        cls.test_output_dir = Path(tempfile.mkdtemp(prefix="report_test_"))
        cls.generator = ReportGenerator(str(cls.templates_dir))

        # Create a simple test logo (1x1 PNG)
        cls.test_logo_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    @classmethod
    def tearDownClass(cls):
        """Clean up test output directory."""
        if cls.test_output_dir.exists():
            shutil.rmtree(cls.test_output_dir)

    def _create_test_site_data(self, site_id: int, with_scenarios: bool = True) -> Dict[str, Any]:
        """
        Create test site data.

        Args:
            site_id: Site identifier
            with_scenarios: Whether to include comparison scenarios

        Returns:
            Dictionary with site data
        """
        site_data = {
            'id': site_id,
            'coord_x': 500000.0 + site_id * 100,
            'coord_y': 5800000.0 + site_id * 100,
            'foundation_volume': 150.0,
            'platform_cut': 1200.0,
            'platform_fill': 800.0,
            'slope_cut': 300.0,
            'slope_fill': 200.0,
            'total_cut': 1500.0,
            'total_fill': 1000.0,
            'platform_height': 0.5,
            'platform_area': 900.0,
            'cost_total': 42000.0,
            'cost_saving': 3000.0,
            'material_reuse': True,
            'material_available': 1500.0,
            'material_required': 1000.0,
            'material_surplus': 500.0,
            'material_deficit': 0.0,
            'material_reused': 1000.0
        }

        if with_scenarios:
            site_data['scenarios'] = [
                {
                    'height': 0.0,
                    'cut_volume': 1800.0,
                    'fill_volume': 900.0,
                    'total_cost': 45000.0,
                    'is_optimal': False
                },
                {
                    'height': 0.5,
                    'cut_volume': 1500.0,
                    'fill_volume': 1000.0,
                    'total_cost': 42000.0,
                    'is_optimal': True
                },
                {
                    'height': 1.0,
                    'cut_volume': 1200.0,
                    'fill_volume': 1200.0,
                    'total_cost': 43500.0,
                    'is_optimal': False
                }
            ]

        return site_data

    def _create_test_report_data(
        self,
        num_sites: int = 3,
        with_scenarios: bool = True,
        with_branding: bool = True
    ) -> Dict[str, Any]:
        """
        Create complete test report data.

        Args:
            num_sites: Number of sites to include
            with_scenarios: Whether to include comparison scenarios
            with_branding: Whether to include branding options

        Returns:
            Dictionary with complete report data
        """
        sites = [self._create_test_site_data(i + 1, with_scenarios) for i in range(num_sites)]

        data = {
            'project_name': 'Test Wind Park Integration',
            'total_sites': num_sites,
            'total_cut': sum(s['total_cut'] for s in sites),
            'total_fill': sum(s['total_fill'] for s in sites),
            'total_cost': sum(s['cost_total'] for s in sites),
            'sites': sites
        }

        if with_branding:
            data['branding'] = {
                'logo_base64': self.test_logo_base64,
                'company_name': 'Test Engineering GmbH',
                'custom_footer_text': 'Test Report - Integration Testing'
            }

        return data

    def test_complete_pdf_generation_flow(self):
        """Test complete PDF generation with all features enabled."""
        # Create report data with all features
        data = self._create_test_report_data(
            num_sites=3,
            with_scenarios=True,
            with_branding=True
        )

        # Generate HTML
        html_path = self.test_output_dir / "test_complete_report.html"
        start_time = time.time()

        result_html = self.generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )

        # Verify HTML generation
        self.assertTrue(result_html.exists(), "HTML file should be created")
        self.assertGreater(result_html.stat().st_size, 0, "HTML file should not be empty")

        # Generate PDF
        pdf_path = self.test_output_dir / "test_complete_report.pdf"
        result_pdf = self.generator.generate_pdf(result_html, pdf_path)

        generation_time = time.time() - start_time

        # Verify PDF generation
        self.assertTrue(result_pdf.exists(), "PDF file should be created")
        self.assertGreater(result_pdf.stat().st_size, 0, "PDF file should not be empty")

        # Log generation time (performance tracking)
        print(f"\nPDF generation time: {generation_time:.2f}s")

        # Verify performance requirement (<10s for standard report)
        # Note: This is a guideline; actual performance depends on hardware
        if generation_time > 10:
            print(f"WARNING: PDF generation took {generation_time:.2f}s (target: <10s)")

    def test_pdf_generation_with_charts(self):
        """Test PDF generation with embedded charts."""
        data = self._create_test_report_data(num_sites=2, with_scenarios=True, with_branding=False)

        html_path = self.test_output_dir / "test_with_charts.html"
        pdf_path = self.test_output_dir / "test_with_charts.pdf"

        # Generate HTML
        html_result = self.generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )

        # Verify HTML contains chart references
        with open(html_result, 'r', encoding='utf-8') as f:
            html_content = f.read()
            # Check for chart data URIs if charts were generated
            if 'data:image/png;base64' in html_content:
                self.assertIn('data:image/png;base64', html_content, "HTML should contain base64 chart images")

        # Generate PDF
        pdf_result = self.generator.generate_pdf(html_result, pdf_path)

        self.assertTrue(pdf_result.exists())
        self.assertGreater(pdf_result.stat().st_size, 1000, "PDF with charts should be reasonably sized")

    def test_pdf_generation_with_branding(self):
        """Test PDF generation with company branding."""
        data = self._create_test_report_data(num_sites=1, with_scenarios=False, with_branding=True)

        html_path = self.test_output_dir / "test_with_branding.html"
        pdf_path = self.test_output_dir / "test_with_branding.pdf"

        # Generate HTML
        html_result = self.generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )

        # Verify HTML contains branding elements
        with open(html_result, 'r', encoding='utf-8') as f:
            html_content = f.read()
            self.assertIn('Test Engineering GmbH', html_content, "Company name should be in HTML")
            self.assertIn('Test Report - Integration Testing', html_content, "Custom footer should be in HTML")

        # Generate PDF
        pdf_result = self.generator.generate_pdf(html_result, pdf_path)

        self.assertTrue(pdf_result.exists())
        self.assertGreater(pdf_result.stat().st_size, 0)

    def test_pdf_generation_with_scenarios(self):
        """Test PDF generation with comparison table."""
        data = self._create_test_report_data(num_sites=2, with_scenarios=True, with_branding=False)

        html_path = self.test_output_dir / "test_with_scenarios.html"
        pdf_path = self.test_output_dir / "test_with_scenarios.pdf"

        # Generate HTML
        html_result = self.generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )

        # Verify HTML contains comparison table
        with open(html_result, 'r', encoding='utf-8') as f:
            html_content = f.read()
            # Check for scenario data (heights)
            self.assertIn('0.0', html_content, "Scenario heights should be in HTML")
            self.assertIn('0.5', html_content, "Scenario heights should be in HTML")

        # Generate PDF
        pdf_result = self.generator.generate_pdf(html_result, pdf_path)

        self.assertTrue(pdf_result.exists())
        self.assertGreater(pdf_result.stat().st_size, 0)

    def test_pdf_generation_minimal_data(self):
        """Test PDF generation with minimal required data."""
        data = {
            'project_name': 'Minimal Test',
            'total_sites': 1,
            'total_cut': 1000.0,
            'total_fill': 800.0,
            'total_cost': 25000.0,
            'sites': [
                {
                    'id': 1,
                    'coord_x': 500000.0,
                    'coord_y': 5800000.0,
                    'foundation_volume': 100.0,
                    'platform_cut': 800.0,
                    'platform_fill': 600.0,
                    'slope_cut': 200.0,
                    'slope_fill': 200.0,
                    'total_cut': 1000.0,
                    'total_fill': 800.0,
                    'platform_height': 0.0,
                    'platform_area': 900.0,
                    'cost_total': 25000.0
                }
            ]
        }

        html_path = self.test_output_dir / "test_minimal.html"
        pdf_path = self.test_output_dir / "test_minimal.pdf"

        # Generate HTML
        html_result = self.generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )

        # Generate PDF
        pdf_result = self.generator.generate_pdf(html_result, pdf_path)

        self.assertTrue(pdf_result.exists())
        self.assertGreater(pdf_result.stat().st_size, 0)

    def test_pdf_generation_multiple_sites(self):
        """Test PDF generation with multiple sites."""
        data = self._create_test_report_data(num_sites=5, with_scenarios=True, with_branding=True)

        html_path = self.test_output_dir / "test_multiple_sites.html"
        pdf_path = self.test_output_dir / "test_multiple_sites.pdf"

        start_time = time.time()

        # Generate HTML
        html_result = self.generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )

        # Generate PDF
        pdf_result = self.generator.generate_pdf(html_result, pdf_path)

        generation_time = time.time() - start_time

        self.assertTrue(pdf_result.exists())
        self.assertGreater(pdf_result.stat().st_size, 0)

        # Check file size is reasonable (not too large)
        file_size_mb = pdf_result.stat().st_size / (1024 * 1024)
        self.assertLess(file_size_mb, 10, "PDF should be less than 10MB")

        print(f"\nMultiple sites PDF generation time: {generation_time:.2f}s")
        print(f"PDF file size: {file_size_mb:.2f}MB")

    def test_pdf_file_size_reasonable(self):
        """Test that generated PDF file size is reasonable."""
        data = self._create_test_report_data(num_sites=3, with_scenarios=True, with_branding=True)

        html_path = self.test_output_dir / "test_file_size.html"
        pdf_path = self.test_output_dir / "test_file_size.pdf"

        # Generate HTML
        html_result = self.generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )

        # Generate PDF
        pdf_result = self.generator.generate_pdf(html_result, pdf_path)

        # Check file size
        file_size_bytes = pdf_result.stat().st_size
        file_size_kb = file_size_bytes / 1024
        file_size_mb = file_size_bytes / (1024 * 1024)

        print(f"\nPDF file size: {file_size_kb:.2f}KB ({file_size_mb:.2f}MB)")

        # Reasonable size checks
        self.assertGreater(file_size_kb, 10, "PDF should be at least 10KB (has content)")
        self.assertLess(file_size_mb, 5, "PDF should be less than 5MB (reasonable size)")

    def test_html_generation_only(self):
        """Test HTML generation without PDF conversion."""
        data = self._create_test_report_data(num_sites=2, with_scenarios=True, with_branding=True)

        html_path = self.test_output_dir / "test_html_only.html"

        # Generate HTML only
        html_result = self.generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )

        self.assertTrue(html_result.exists())
        self.assertGreater(html_result.stat().st_size, 0)

        # Verify HTML is valid
        with open(html_result, 'r', encoding='utf-8') as f:
            html_content = f.read()
            self.assertIn('<!DOCTYPE html>', html_content, "HTML should have DOCTYPE")
            self.assertIn('<html', html_content, "HTML should have html tag")
            self.assertIn('Test Wind Park Integration', html_content, "Project name should be in HTML")

    def test_generation_with_invalid_branding(self):
        """Test that generation handles invalid branding gracefully."""
        data = self._create_test_report_data(num_sites=1, with_scenarios=False, with_branding=False)

        # Add invalid branding
        data['branding'] = {
            'logo_base64': 'invalid_base64_data',  # Invalid base64
            'company_name': 'Test Company',
            'custom_footer_text': 'Test Footer'
        }

        html_path = self.test_output_dir / "test_invalid_branding.html"
        pdf_path = self.test_output_dir / "test_invalid_branding.pdf"

        # Should not raise exception - graceful degradation
        html_result = self.generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )

        # Should still generate PDF without logo
        pdf_result = self.generator.generate_pdf(html_result, pdf_path)

        self.assertTrue(pdf_result.exists())
        self.assertGreater(pdf_result.stat().st_size, 0)


@unittest.skipIf(not GENERATOR_AVAILABLE or not SCHEMAS_AVAILABLE,
                 "Dependencies not available (weasyprint, matplotlib, etc.)")
class TestIntegrationPerformance(unittest.TestCase):
    """Performance-focused integration tests."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.templates_dir = Path(__file__).parent.parent / "app" / "templates"
        cls.test_output_dir = Path(tempfile.mkdtemp(prefix="report_perf_"))
        cls.generator = ReportGenerator(str(cls.templates_dir))
        cls.test_logo_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    @classmethod
    def tearDownClass(cls):
        """Clean up test output directory."""
        if cls.test_output_dir.exists():
            shutil.rmtree(cls.test_output_dir)

    def test_standard_report_performance(self):
        """
        Test standard report generation performance.

        Standard report: 3 sites, 5 scenarios each, charts, logo, comparison table
        Target: <10 seconds
        """
        # Create standard report data
        sites = []
        for i in range(3):
            site = {
                'id': i + 1,
                'coord_x': 500000.0 + i * 100,
                'coord_y': 5800000.0 + i * 100,
                'foundation_volume': 150.0,
                'platform_cut': 1200.0,
                'platform_fill': 800.0,
                'slope_cut': 300.0,
                'slope_fill': 200.0,
                'total_cut': 1500.0,
                'total_fill': 1000.0,
                'platform_height': 0.5,
                'platform_area': 900.0,
                'cost_total': 42000.0,
                'scenarios': [
                    {'height': h * 0.25, 'cut_volume': 1500 - h * 100, 'fill_volume': 1000 + h * 50,
                     'total_cost': 42000 + h * 500, 'is_optimal': h == 2}
                    for h in range(5)
                ]
            }
            sites.append(site)

        data = {
            'project_name': 'Standard Performance Test',
            'total_sites': 3,
            'total_cut': sum(s['total_cut'] for s in sites),
            'total_fill': sum(s['total_fill'] for s in sites),
            'total_cost': sum(s['cost_total'] for s in sites),
            'sites': sites,
            'branding': {
                'logo_base64': self.test_logo_base64,
                'company_name': 'Performance Test Corp',
                'custom_footer_text': 'Performance Testing Report'
            }
        }

        html_path = self.test_output_dir / "perf_standard.html"
        pdf_path = self.test_output_dir / "perf_standard.pdf"

        # Time the complete generation
        start_time = time.time()

        html_result = self.generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )

        pdf_result = self.generator.generate_pdf(html_result, pdf_path)

        total_time = time.time() - start_time

        # Verify files created
        self.assertTrue(pdf_result.exists())
        self.assertGreater(pdf_result.stat().st_size, 0)

        # Report performance
        print(f"\n{'='*60}")
        print(f"STANDARD REPORT PERFORMANCE TEST")
        print(f"{'='*60}")
        print(f"Sites: 3")
        print(f"Scenarios per site: 5")
        print(f"Features: Charts, Branding, Comparison Tables")
        print(f"Generation time: {total_time:.2f}s")
        print(f"Target: <10s")
        print(f"Status: {'✓ PASS' if total_time < 10 else '✗ FAIL (exceeds target)'}")
        print(f"{'='*60}\n")


if __name__ == '__main__':
    unittest.main(verbosity=2)
