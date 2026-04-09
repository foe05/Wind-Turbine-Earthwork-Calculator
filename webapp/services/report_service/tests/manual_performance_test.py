#!/usr/bin/env python3
"""
Manual Performance Test for PDF Report Generation

This script generates a standard WKA report with all features enabled and
measures the generation time to verify it meets the <10 seconds requirement.

Standard report configuration:
- 3 sites
- 5 scenarios per site
- All charts enabled
- Company logo
- Custom branding
- Comparison tables

Requirements:
- All dependencies from requirements.txt must be installed
- Run from report_service directory

Usage:
    python3 tests/manual_performance_test.py

"""

import sys
import os
import time
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.core.generator import ReportGenerator
except ImportError as e:
    print(f"ERROR: Could not import ReportGenerator: {e}")
    print("Make sure all dependencies are installed: pip install -r requirements.txt")
    sys.exit(1)


def create_standard_report_data():
    """
    Create standard report data for performance testing.

    Returns:
        Dictionary with complete report data including 3 sites, 5 scenarios each,
        charts, branding, and comparison tables
    """
    # Create test logo (1x1 PNG - minimal valid PNG)
    test_logo_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    # Create 3 sites with 5 scenarios each
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
            'cost_saving': 3000.0,
            'material_reuse': True,
            'material_available': 1500.0,
            'material_required': 1000.0,
            'material_surplus': 500.0,
            'material_deficit': 0.0,
            'material_reused': 1000.0,
            'scenarios': []
        }

        # Add 5 scenarios per site
        for h in range(5):
            scenario = {
                'height': h * 0.25,
                'cut_volume': 1500 - h * 100,
                'fill_volume': 1000 + h * 50,
                'total_cost': 42000 + h * 500,
                'is_optimal': h == 2  # Mark middle scenario as optimal
            }
            site['scenarios'].append(scenario)

        sites.append(site)

    # Create complete report data
    data = {
        'project_name': 'Standard Performance Test - WKA Report',
        'total_sites': 3,
        'total_cut': sum(s['total_cut'] for s in sites),
        'total_fill': sum(s['total_fill'] for s in sites),
        'total_cost': sum(s['cost_total'] for s in sites),
        'sites': sites,
        'branding': {
            'logo_base64': test_logo_base64,
            'company_name': 'Performance Test Engineering GmbH',
            'custom_footer_text': f'Performance Test Report - Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        }
    }

    return data


def run_performance_test():
    """
    Run the performance test for standard WKA report generation.

    Measures:
    - HTML generation time
    - PDF conversion time
    - Total generation time
    - File sizes

    Returns:
        Dictionary with performance metrics
    """
    print("="*70)
    print("PDF REPORT GENERATION - PERFORMANCE TEST")
    print("="*70)
    print()

    # Setup
    templates_dir = Path(__file__).parent.parent / "app" / "templates"
    test_output_dir = Path(tempfile.mkdtemp(prefix="perf_test_"))

    print(f"Templates directory: {templates_dir}")
    print(f"Output directory: {test_output_dir}")
    print()

    # Initialize generator
    print("Initializing report generator...")
    generator = ReportGenerator(str(templates_dir))
    print("✓ Generator initialized")
    print()

    # Create test data
    print("Creating standard report data...")
    print("  - 3 sites")
    print("  - 5 scenarios per site")
    print("  - All charts enabled")
    print("  - Company logo included")
    print("  - Custom branding")
    print("  - Comparison tables")
    data = create_standard_report_data()
    print("✓ Test data created")
    print()

    # Define output paths
    html_path = test_output_dir / "performance_test_report.html"
    pdf_path = test_output_dir / "performance_test_report.pdf"

    # Start timing
    print("-" * 70)
    print("STARTING GENERATION...")
    print("-" * 70)
    overall_start = time.time()

    # Generate HTML
    print("\n[1/2] Generating HTML report...")
    html_start = time.time()
    try:
        html_result = generator.generate_report(
            template='wka',
            data=data,
            output_path=html_path,
            format='html'
        )
        html_time = time.time() - html_start
        print(f"✓ HTML generated in {html_time:.2f}s")
        print(f"  File: {html_result}")
        print(f"  Size: {html_result.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"✗ HTML generation failed: {e}")
        shutil.rmtree(test_output_dir)
        return None

    # Generate PDF
    print("\n[2/2] Converting to PDF...")
    pdf_start = time.time()
    try:
        pdf_result = generator.generate_pdf(html_result, pdf_path)
        pdf_time = time.time() - pdf_start
        print(f"✓ PDF generated in {pdf_time:.2f}s")
        print(f"  File: {pdf_result}")
        print(f"  Size: {pdf_result.stat().st_size / 1024:.1f} KB ({pdf_result.stat().st_size / (1024*1024):.2f} MB)")
    except Exception as e:
        print(f"✗ PDF generation failed: {e}")
        shutil.rmtree(test_output_dir)
        return None

    # Calculate total time
    total_time = time.time() - overall_start

    # Print results
    print()
    print("="*70)
    print("PERFORMANCE TEST RESULTS")
    print("="*70)
    print()
    print(f"HTML Generation Time:  {html_time:>8.2f}s")
    print(f"PDF Conversion Time:   {pdf_time:>8.2f}s")
    print(f"{'─'*70}")
    print(f"TOTAL TIME:            {total_time:>8.2f}s")
    print()
    print(f"Target:                {'>10.00'}s")
    print()

    # Determine pass/fail
    passed = total_time < 10.0
    if passed:
        print(f"✓✓✓ PERFORMANCE TEST PASSED ✓✓✓")
        print(f"    Report generated in {total_time:.2f}s (target: <10s)")
    else:
        print(f"✗✗✗ PERFORMANCE TEST FAILED ✗✗✗")
        print(f"    Report took {total_time:.2f}s (exceeds 10s target by {total_time - 10:.2f}s)")

    print()
    print("="*70)
    print()

    # File information
    print("Generated Files:")
    print(f"  HTML: {html_result}")
    print(f"  PDF:  {pdf_result}")
    print()
    print("Note: Files are in temporary directory and will be cleaned up.")
    print("      To keep files, copy them before script exits.")
    print()

    # Collect metrics
    metrics = {
        'html_time': html_time,
        'pdf_time': pdf_time,
        'total_time': total_time,
        'html_size_kb': html_result.stat().st_size / 1024,
        'pdf_size_kb': pdf_result.stat().st_size / 1024,
        'passed': passed,
        'html_path': str(html_result),
        'pdf_path': str(pdf_result),
        'output_dir': str(test_output_dir)
    }

    return metrics


def main():
    """Main entry point for performance test."""
    print()
    print("Starting performance test...")
    print()

    try:
        metrics = run_performance_test()

        if metrics is None:
            print("Performance test aborted due to errors.")
            return 1

        # Wait for user input before cleanup
        input("Press Enter to clean up temporary files and exit...")

        # Cleanup
        if os.path.exists(metrics['output_dir']):
            shutil.rmtree(metrics['output_dir'])
            print(f"✓ Cleaned up temporary directory: {metrics['output_dir']}")

        # Exit with appropriate code
        return 0 if metrics['passed'] else 1

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
