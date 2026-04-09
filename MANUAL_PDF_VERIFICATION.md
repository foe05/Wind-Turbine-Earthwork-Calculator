# Manual PDF Verification for Multi-Site Report Generator

## Overview
This document describes how to manually verify the PDF export functionality for the multi-site report generator.

## Implementation Details

### Changes Made
1. **Added WeasyPrint dependency** to `requirements.txt`:
   - `weasyprint>=56.0`

2. **Added PDF export method** to `MultiSiteReportGenerator`:
   - `generate_pdf(html_path: str, output_path: str)` method
   - Follows the pattern from `webapp/services/report_service/app/core/generator.py`
   - Includes custom CSS for A4 page layout with 2cm margins

### Pattern Followed
The implementation follows the exact pattern from the reference file:
- Uses `weasyprint.HTML` and `weasyprint.CSS`
- Custom `@page` CSS for PDF formatting
- Proper path handling with `pathlib.Path`
- Directory creation with `mkdir(parents=True, exist_ok=True)`
- Comprehensive logging

## Manual Verification Steps

### Prerequisites
- QGIS with the Wind Turbine Earthwork Calculator V2 plugin installed
- Multiple wind turbine sites loaded in the project
- WeasyPrint will be automatically installed on first plugin run

### Test Procedure

1. **Open QGIS** with the plugin installed

2. **Load test data**:
   - Create or load a project with 3+ wind turbine sites
   - Ensure each site has valid terrain data

3. **Generate HTML report**:
   ```python
   from windturbine_earthwork_calculator_v2.core.multi_site_report_generator import MultiSiteReportGenerator

   # Assuming site_results is populated from your calculation
   generator = MultiSiteReportGenerator(site_results)

   # Generate HTML
   html_path = "/path/to/output/multi_site_report.html"
   generator.generate_html(html_path, project_name="Test Project")
   ```

4. **Generate PDF from HTML**:
   ```python
   # Generate PDF
   pdf_path = "/path/to/output/multi_site_report.pdf"
   generator.generate_pdf(html_path, pdf_path)
   ```

5. **Verify PDF output**:
   - Open the generated PDF file
   - Check that all sections are visible:
     - ✓ Header with project name and date
     - ✓ Project summary with total volumes
     - ✓ Statistical analysis tables
     - ✓ Site ranking table
     - ✓ Detailed site comparison
     - ✓ Individual site details (one per site)
     - ✓ Cost breakdown table
     - ✓ Footer
   - Verify formatting:
     - ✓ Tables are properly formatted
     - ✓ Colors and styling are preserved
     - ✓ Text is readable (12px font size)
     - ✓ Pages have proper margins (2cm)
     - ✓ No content is cut off

6. **Test edge cases**:
   - Generate PDF with 1 site
   - Generate PDF with 10+ sites
   - Verify long site names don't break layout
   - Verify large volume numbers are formatted correctly

## Expected Behavior

### Success Criteria
- PDF file is created successfully
- File size is reasonable (> 50KB for typical 3-site report)
- All sections from HTML report are present in PDF
- Formatting and styling are preserved
- PDF opens in standard PDF readers (Adobe Reader, Chrome, Firefox)
- Content is searchable (text is not rasterized)

### Logging Output
You should see log messages like:
```
Generating PDF from HTML: /path/to/report.html
  ✓ PDF report generated: /path/to/report.pdf
```

## Troubleshooting

### WeasyPrint Installation Issues
If WeasyPrint fails to install automatically:
```bash
# In QGIS Python console or plugin environment
pip install weasyprint>=56.0
```

### Missing System Dependencies
WeasyPrint requires system libraries (cairo, pango). On Linux:
```bash
sudo apt-get install python3-weasyprint
```

### PDF Generation Errors
- Check that HTML file exists and is valid
- Verify output directory has write permissions
- Check QGIS log for detailed error messages

## Notes
- The HTML report must be generated before calling `generate_pdf()`
- PDF generation may take a few seconds for large reports
- WeasyPrint preserves most CSS styling, but some advanced CSS features may not be supported
