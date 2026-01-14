#!/usr/bin/env python3
"""
Visual QA Test for PDF Report Generation

This script generates sample PDF reports with different configurations
for manual visual quality assurance. The generated PDFs should be
manually inspected to verify:

1. Charts are clear and properly labeled
2. Comparison tables are readable and properly formatted
3. Branding (logo, company name, footer) appears correctly
4. Page breaks are appropriate (no content split awkwardly)
5. Overall layout and formatting is professional

Generated PDFs:
- visual_qa_complete.pdf: Full featured report (all enhancements)
- visual_qa_minimal.pdf: Minimal report (basic features only)
- visual_qa_multi_site.pdf: Multiple sites report (5 sites)
- visual_qa_no_branding.pdf: Report without branding
- visual_qa_no_scenarios.pdf: Report without comparison table

Usage:
    python3 tests/visual_qa_test.py

The script will generate PDFs in a 'visual_qa_output' directory
and keep them for manual inspection.
"""

import sys
import os
import time
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


def create_test_logo_base64():
    """
    Create a simple test logo (red 100x100 PNG).

    Returns:
        Base64-encoded PNG image
    """
    # This is a small red square PNG for testing
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="


def create_complete_report_data():
    """
    Create complete report data with all features enabled.

    Returns:
        Dictionary with complete report data
    """
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
            'scenarios': [
                {
                    'height': h * 0.25,
                    'cut_volume': 1500 - h * 100,
                    'fill_volume': 1000 + h * 50,
                    'total_cost': 42000 + h * 500,
                    'is_optimal': h == 2
                }
                for h in range(5)
            ]
        }
        sites.append(site)

    return {
        'project_name': 'Visual QA Test - Complete Report',
        'total_sites': 3,
        'total_cut': sum(s['total_cut'] for s in sites),
        'total_fill': sum(s['total_fill'] for s in sites),
        'total_cost': sum(s['cost_total'] for s in sites),
        'sites': sites,
        'branding': {
            'logo_base64': create_test_logo_base64(),
            'company_name': 'Wind Engineering GmbH',
            'custom_footer_text': f'Visual QA Test Report - Generated {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
        }
    }


def create_minimal_report_data():
    """
    Create minimal report data (single site, no scenarios, no branding).

    Returns:
        Dictionary with minimal report data
    """
    return {
        'project_name': 'Visual QA Test - Minimal Report',
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


def create_multi_site_report_data():
    """
    Create report with multiple sites (5 sites).

    Returns:
        Dictionary with multi-site report data
    """
    sites = []
    for i in range(5):
        site = {
            'id': i + 1,
            'coord_x': 500000.0 + i * 200,
            'coord_y': 5800000.0 + i * 150,
            'foundation_volume': 120.0 + i * 10,
            'platform_cut': 1000.0 + i * 200,
            'platform_fill': 700.0 + i * 150,
            'slope_cut': 250.0 + i * 50,
            'slope_fill': 180.0 + i * 40,
            'total_cut': 1250.0 + i * 250,
            'total_fill': 880.0 + i * 190,
            'platform_height': 0.25 * (i % 3),
            'platform_area': 850.0 + i * 50,
            'cost_total': 38000.0 + i * 4000,
            'cost_saving': 2500.0 + i * 500,
            'material_reuse': i % 2 == 0,
            'material_available': 1250.0 + i * 250,
            'material_required': 880.0 + i * 190,
            'material_surplus': (1250.0 + i * 250) - (880.0 + i * 190) if i % 2 == 0 else 0,
            'material_deficit': 0 if i % 2 == 0 else (880.0 + i * 190) - (1250.0 + i * 250),
            'material_reused': min(1250.0 + i * 250, 880.0 + i * 190),
            'scenarios': [
                {
                    'height': h * 0.3,
                    'cut_volume': (1250.0 + i * 250) - h * 80,
                    'fill_volume': (880.0 + i * 190) + h * 60,
                    'total_cost': (38000.0 + i * 4000) + h * 600,
                    'is_optimal': h == 1
                }
                for h in range(4)
            ]
        }
        sites.append(site)

    return {
        'project_name': 'Visual QA Test - Multi-Site Report (5 Sites)',
        'total_sites': 5,
        'total_cut': sum(s['total_cut'] for s in sites),
        'total_fill': sum(s['total_fill'] for s in sites),
        'total_cost': sum(s['cost_total'] for s in sites),
        'sites': sites,
        'branding': {
            'logo_base64': create_test_logo_base64(),
            'company_name': 'Multi-Site Engineering Corp',
            'custom_footer_text': 'Multi-Site Visual QA Test'
        }
    }


def create_no_branding_report_data():
    """
    Create report without branding (for comparison).

    Returns:
        Dictionary with report data (no branding)
    """
    data = create_complete_report_data()
    data['project_name'] = 'Visual QA Test - No Branding'
    del data['branding']
    return data


def create_no_scenarios_report_data():
    """
    Create report without comparison scenarios.

    Returns:
        Dictionary with report data (no scenarios)
    """
    data = create_complete_report_data()
    data['project_name'] = 'Visual QA Test - No Scenarios'
    for site in data['sites']:
        if 'scenarios' in site:
            del site['scenarios']
    return data


def generate_visual_qa_pdfs():
    """
    Generate all Visual QA test PDFs.

    Returns:
        Dictionary with generation results
    """
    print("="*70)
    print("VISUAL QA TEST - PDF REPORT GENERATION")
    print("="*70)
    print()

    # Setup
    templates_dir = Path(__file__).parent.parent / "app" / "templates"
    output_dir = Path(__file__).parent / "visual_qa_output"
    output_dir.mkdir(exist_ok=True)

    print(f"Templates directory: {templates_dir}")
    print(f"Output directory: {output_dir}")
    print()

    # Initialize generator
    print("Initializing report generator...")
    generator = ReportGenerator(str(templates_dir))
    print("✓ Generator initialized")
    print()

    # Test configurations
    test_cases = [
        {
            'name': 'Complete Report (All Features)',
            'filename': 'visual_qa_complete',
            'data_func': create_complete_report_data,
            'description': 'Full featured report with charts, branding, and comparison tables'
        },
        {
            'name': 'Minimal Report',
            'filename': 'visual_qa_minimal',
            'data_func': create_minimal_report_data,
            'description': 'Basic report with single site, no scenarios, no branding'
        },
        {
            'name': 'Multi-Site Report (5 Sites)',
            'filename': 'visual_qa_multi_site',
            'data_func': create_multi_site_report_data,
            'description': 'Report with 5 sites to test page breaks and layout'
        },
        {
            'name': 'No Branding',
            'filename': 'visual_qa_no_branding',
            'data_func': create_no_branding_report_data,
            'description': 'Report without logo or custom footer'
        },
        {
            'name': 'No Scenarios',
            'filename': 'visual_qa_no_scenarios',
            'data_func': create_no_scenarios_report_data,
            'description': 'Report without comparison table'
        }
    ]

    results = []
    total_start = time.time()

    print("-" * 70)
    print("GENERATING TEST PDFs...")
    print("-" * 70)
    print()

    for i, test_case in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}] {test_case['name']}")
        print(f"    {test_case['description']}")

        try:
            # Generate data
            data = test_case['data_func']()

            # Generate HTML
            html_path = output_dir / f"{test_case['filename']}.html"
            start_time = time.time()

            html_result = generator.generate_report(
                template='wka',
                data=data,
                output_path=html_path,
                format='html'
            )

            # Generate PDF
            pdf_path = output_dir / f"{test_case['filename']}.pdf"
            pdf_result = generator.generate_pdf(html_result, pdf_path)

            generation_time = time.time() - start_time
            file_size_kb = pdf_result.stat().st_size / 1024

            print(f"    ✓ Generated in {generation_time:.2f}s ({file_size_kb:.1f} KB)")
            print(f"      PDF: {pdf_result}")

            results.append({
                'name': test_case['name'],
                'pdf_path': str(pdf_result),
                'html_path': str(html_result),
                'time': generation_time,
                'size_kb': file_size_kb,
                'success': True
            })

        except Exception as e:
            print(f"    ✗ Failed: {e}")
            results.append({
                'name': test_case['name'],
                'success': False,
                'error': str(e)
            })

        print()

    total_time = time.time() - total_start

    # Print summary
    print("="*70)
    print("VISUAL QA TEST SUMMARY")
    print("="*70)
    print()

    successful = [r for r in results if r.get('success')]
    failed = [r for r in results if not r.get('success')]

    print(f"Total Tests: {len(results)}")
    print(f"Successful:  {len(successful)}")
    print(f"Failed:      {len(failed)}")
    print(f"Total Time:  {total_time:.2f}s")
    print()

    if successful:
        print("Generated PDFs:")
        for result in successful:
            print(f"  ✓ {result['name']}")
            print(f"    File: {result['pdf_path']}")
            print(f"    Size: {result['size_kb']:.1f} KB")
            print(f"    Time: {result['time']:.2f}s")
            print()

    if failed:
        print("Failed Tests:")
        for result in failed:
            print(f"  ✗ {result['name']}")
            print(f"    Error: {result['error']}")
            print()

    print("="*70)
    print()
    print("NEXT STEPS - MANUAL VISUAL INSPECTION")
    print("="*70)
    print()
    print("Please open the generated PDF files and verify:")
    print()
    print("1. CHARTS QUALITY:")
    print("   - Charts are clear and not pixelated")
    print("   - Axes are properly labeled")
    print("   - Legend is visible and readable")
    print("   - Colors are distinct and professional")
    print("   - Chart titles are descriptive")
    print()
    print("2. COMPARISON TABLE:")
    print("   - Table is properly formatted")
    print("   - Optimal scenario is highlighted (green background)")
    print("   - All columns are aligned")
    print("   - Numbers are properly formatted")
    print("   - OPTIMAL badge is visible")
    print()
    print("3. BRANDING:")
    print("   - Logo appears in header (if provided)")
    print("   - Logo is properly sized and positioned")
    print("   - Company name is visible and styled")
    print("   - Custom footer text appears correctly")
    print()
    print("4. PAGE BREAKS:")
    print("   - Charts are not split across pages")
    print("   - Tables are not split inappropriately")
    print("   - Site cards stay together")
    print("   - Headers stay with their content")
    print()
    print("5. OVERALL LAYOUT:")
    print("   - Professional appearance")
    print("   - Consistent spacing and alignment")
    print("   - Readable font sizes")
    print("   - No overlapping content")
    print("   - Proper margins on all pages")
    print()
    print("="*70)
    print()
    print(f"Output directory: {output_dir.absolute()}")
    print()

    return results


def main():
    """Main entry point for Visual QA test."""
    print()
    print("Starting Visual QA test...")
    print()

    try:
        results = generate_visual_qa_pdfs()

        # Check if any succeeded
        successful = [r for r in results if r.get('success')]
        if not successful:
            print("ERROR: No PDFs were generated successfully.")
            return 1

        print("Visual QA test completed successfully.")
        print("Please manually inspect the generated PDFs.")
        print()

        return 0

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
