"""
Test script for PDF generation from multi-site report
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from windturbine_earthwork_calculator_v2.core.multi_site_report_generator import MultiSiteReportGenerator


def create_test_data():
    """Create sample test data for multi-site report"""
    site_results = [
        {
            'site_id': 'WEA-01',
            'site_name': 'Standort Nord',
            'coordinates': (500000, 5800000),
            'results': {
                'total_cut': 1500.0,
                'total_fill': 2200.0,
                'net_volume': -700.0,
                'gravel_fill_external': 500.0,
                'crane_height': 450.5,
                'platform_height': 450.5,
                'terrain_min': 445.0,
                'terrain_max': 455.0,
                'terrain_mean': 450.0,
                'total_platform_area': 900.0,
                'platform_area': 900.0,
                'total_area': 1200.0,
                'slope_width': 5.5,
            },
            'config': {
                'slope_angle': 45.0
            }
        },
        {
            'site_id': 'WEA-02',
            'site_name': 'Standort Süd',
            'coordinates': (501000, 5799000),
            'results': {
                'total_cut': 1800.0,
                'total_fill': 1600.0,
                'net_volume': 200.0,
                'gravel_fill_external': 300.0,
                'crane_height': 425.8,
                'platform_height': 425.8,
                'terrain_min': 420.0,
                'terrain_max': 432.0,
                'terrain_mean': 426.0,
                'total_platform_area': 900.0,
                'platform_area': 900.0,
                'total_area': 1200.0,
                'slope_width': 5.5,
            },
            'config': {
                'slope_angle': 45.0
            }
        },
        {
            'site_id': 'WEA-03',
            'site_name': 'Standort Ost',
            'coordinates': (502000, 5800500),
            'results': {
                'total_cut': 2100.0,
                'total_fill': 1900.0,
                'net_volume': 200.0,
                'gravel_fill_external': 400.0,
                'crane_height': 465.2,
                'platform_height': 465.2,
                'terrain_min': 460.0,
                'terrain_max': 472.0,
                'terrain_mean': 466.0,
                'total_platform_area': 900.0,
                'platform_area': 900.0,
                'total_area': 1200.0,
                'slope_width': 5.5,
            },
            'config': {
                'slope_angle': 45.0
            }
        }
    ]

    return site_results


def test_pdf_generation():
    """Test PDF generation"""
    print("Testing PDF generation from multi-site report...")

    # Create test data
    site_results = create_test_data()

    # Initialize report generator
    generator = MultiSiteReportGenerator(site_results)

    # Create output directory
    output_dir = Path(__file__).parent / 'test_output'
    output_dir.mkdir(exist_ok=True)

    # Generate HTML report
    html_path = output_dir / 'test_multi_site_report.html'
    print(f"Generating HTML report: {html_path}")
    generator.generate_html(str(html_path), project_name="Test Windpark")

    # Verify HTML was created
    if not html_path.exists():
        print("ERROR: HTML report was not created!")
        return False
    print(f"✓ HTML report created successfully ({html_path.stat().st_size} bytes)")

    # Generate PDF from HTML
    pdf_path = output_dir / 'test_multi_site_report.pdf'
    print(f"Generating PDF report: {pdf_path}")
    generator.generate_pdf(str(html_path), str(pdf_path))

    # Verify PDF was created
    if not pdf_path.exists():
        print("ERROR: PDF report was not created!")
        return False
    print(f"✓ PDF report created successfully ({pdf_path.stat().st_size} bytes)")

    # Check PDF file size is reasonable (should be > 10KB)
    pdf_size = pdf_path.stat().st_size
    if pdf_size < 10000:
        print(f"WARNING: PDF file size seems small ({pdf_size} bytes)")
        return False

    print(f"\n✓ PDF generation test PASSED!")
    print(f"  HTML: {html_path}")
    print(f"  PDF:  {pdf_path}")
    print(f"\nPlease manually verify the PDF opens correctly and all sections are visible.")

    return True


if __name__ == '__main__':
    try:
        success = test_pdf_generation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
