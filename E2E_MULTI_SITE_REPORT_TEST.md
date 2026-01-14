# End-to-End Manual Test: Multi-Site Comparison Report

## Overview
This document provides step-by-step instructions for performing a complete end-to-end test of the Multi-Site Comparison Report feature in the Wind Turbine Earthwork Calculator V2 QGIS plugin.

## Test Objective
Verify that the multi-site comparison report feature works correctly from site processing through report generation in all formats (HTML, PDF, Excel).

## Prerequisites

### Software Requirements
- QGIS 3.x installed
- Wind Turbine Earthwork Calculator V2 plugin installed
- Python dependencies installed in QGIS environment:
  - `weasyprint>=56.0` (for PDF export)
  - `openpyxl>=3.0.0` (for Excel export)

### Test Data Requirements
- 3 different wind turbine sites with varying terrain characteristics:
  - **Site 1**: Low complexity (minimal earthwork)
  - **Site 2**: Medium complexity (moderate earthwork)
  - **Site 3**: High complexity (significant earthwork)
- Each site should have valid DEM/terrain raster data

## Test Procedure

### Phase 1: Setup and Site Processing

#### Step 1.1: Load Plugin in QGIS
1. Open QGIS
2. Navigate to **Plugins > Manage and Install Plugins**
3. Verify "Wind Turbine Earthwork Calculator V2" is enabled
4. If not enabled, check the plugin and click "Enable Plugin"
5. Verify the plugin icon appears in the QGIS toolbar

**✓ Expected Result**: Plugin loads without errors, icon visible in toolbar

#### Step 1.2: Prepare Test Data
1. Load DEM/terrain raster layer into QGIS
2. Ensure the layer has valid elevation data
3. Verify coordinate reference system (CRS) is appropriate for your region

**✓ Expected Result**: Terrain data displays correctly in QGIS map canvas

#### Step 1.3: Process Site 1 (Low Complexity)
1. Click the plugin icon to open the main dialog
2. Go to the "Berechnung" (Calculation) tab
3. Enter site parameters:
   - **Site ID**: WEA-01
   - **Site Name**: Low Complexity Site
   - **Crane Height**: 420.0 m
   - **Platform Dimensions**: Default values
   - **Slope Angle**: 45°
4. Select the terrain raster layer
5. Click the center point tool and place point on relatively flat terrain
6. Click "Calculate" button
7. Wait for calculation to complete

**✓ Expected Results**:
- Calculation completes without errors
- Results show low earthwork volumes (< 2000 m³ total)
- Site appears in processed sites list

#### Step 1.4: Process Site 2 (Medium Complexity)
1. Repeat steps from 1.3 with different parameters:
   - **Site ID**: WEA-02
   - **Site Name**: Medium Complexity Site
   - **Crane Height**: 440.0 m
   - Place point on moderately sloped terrain
2. Calculate

**✓ Expected Results**:
- Calculation completes successfully
- Results show medium earthwork volumes (2000-4000 m³ total)
- Site appears in processed sites list

#### Step 1.5: Process Site 3 (High Complexity)
1. Repeat steps from 1.3 with different parameters:
   - **Site ID**: WEA-03
   - **Site Name**: High Complexity Site
   - **Crane Height**: 460.0 m
   - Place point on steeply sloped terrain
2. Calculate

**✓ Expected Results**:
- Calculation completes successfully
- Results show high earthwork volumes (> 4000 m³ total)
- Site appears in processed sites list

### Phase 2: Multi-Site Report Tab Navigation

#### Step 2.1: Navigate to Multi-Site Report Tab
1. In the plugin main dialog, locate the tabs at the top
2. Click on "Standortvergleich" (Multi-Site Comparison) tab

**✓ Expected Results**:
- Tab switches successfully
- Multi-site report interface is visible
- No errors in QGIS log

#### Step 2.2: Verify Site Selection UI
1. Locate the "Standortauswahl" (Site Selection) section
2. Verify all 3 processed sites appear in the checkbox list
3. Check that each site shows:
   - Site name
   - Earthwork volume
   - Estimated cost
4. Verify all sites are checked by default

**✓ Expected Results**:
- All 3 sites visible in checkbox list
- Checkboxes are checked by default
- Information displays correctly for each site
- "Select All" and "Deselect All" buttons are present

#### Step 2.3: Test Site Selection Controls
1. Click "Deselect All" button
2. Verify all checkboxes are unchecked
3. Click "Select All" button
4. Verify all checkboxes are checked again
5. Manually uncheck one site
6. Re-check that site

**✓ Expected Results**:
- All selection controls work correctly
- UI updates immediately when buttons are clicked
- Individual checkboxes can be toggled

### Phase 3: HTML Report Generation

#### Step 3.1: Configure HTML Export
1. In "Exportoptionen" (Export Options) section, select format dropdown
2. Select "HTML Report"
3. Click "Browse" button next to output path field
4. Choose output location and filename (e.g., `multi_site_report.html`)
5. Verify cost parameters have default or reasonable values:
   - Cut cost: ~10 €/m³
   - Fill cost: ~8 €/m³
   - Gravel cost: ~25 €/m³

**✓ Expected Results**:
- Format dropdown shows HTML selected
- File browser opens with .html filter
- Output path field shows selected path
- Cost parameters are editable

#### Step 3.2: Generate HTML Report
1. Ensure all 3 sites are selected
2. Click "Bericht generieren" (Generate Report) button
3. Wait for generation to complete
4. Verify success message appears
5. Note the output file path

**✓ Expected Results**:
- Report generation completes without errors
- Success message displays: "Report successfully generated"
- HTML file is created at specified location
- File size is reasonable (> 20 KB)

#### Step 3.3: Verify HTML Report Content
1. Open the generated HTML file in a web browser
2. Verify the following sections are present:

**Header Section**:
- [ ] Project name displayed
- [ ] Generation date/time displayed
- [ ] Professional styling with blue theme

**Project Summary Section**:
- [ ] Number of sites: 3
- [ ] Total estimated costs calculated
- [ ] Average cost per site
- [ ] Total cut volume aggregated
- [ ] Total fill volume aggregated
- [ ] Total earthwork (cut + fill) aggregated
- [ ] Net balance calculated
- [ ] External gravel material aggregated

**Statistical Analysis Section**:
- [ ] Cut volume statistics (average, min, max)
- [ ] Fill volume statistics (average, min, max)
- [ ] Proper formatting of numbers

**Site Ranking Section**:
- [ ] Sites ranked by total earthwork volume (descending)
- [ ] Expected order: High > Medium > Low complexity
- [ ] Rank badges displayed (1st, 2nd, 3rd)
- [ ] Complexity indicators (High/Medium/Low) color-coded
- [ ] Each site shows:
  - Total earthwork moved
  - Cut volume
  - Fill volume
  - Crane height
  - Estimated costs
- [ ] Top 3 recommendation box (if applicable)

**Site Comparison Table**:
- [ ] All 3 sites listed
- [ ] Comparison metrics displayed
- [ ] Relative complexity indicators

**Individual Site Details** (one section per site):
- [ ] Site identification (name, coordinates)
- [ ] Crane height displayed
- [ ] Volume overview cards:
  - Cut volume
  - Fill volume
  - Total moved
  - Net balance
  - External gravel
- [ ] Terrain statistics table (min, max, mean, range)
- [ ] Volume breakdown by component
- [ ] Cost breakdown table with unit prices
- [ ] Platform configuration details

**Cost Breakdown Section**:
- [ ] Breakdown by site
- [ ] Individual cost components
- [ ] Total project cost
- [ ] Cost distribution visualization

**Footer**:
- [ ] Generated by Wind Turbine Earthwork Calculator
- [ ] Timestamp

**✓ Expected Results**: All sections present, data accurate, formatting professional

### Phase 4: PDF Report Generation

#### Step 4.1: Configure PDF Export
1. In format dropdown, select "PDF Report"
2. Click "Browse" button
3. Choose output location and filename (e.g., `multi_site_report.pdf`)
4. Ensure same cost parameters as HTML test
5. Ensure all 3 sites are still selected

**✓ Expected Results**:
- Format changes to PDF
- File browser shows .pdf filter
- Output path updates

#### Step 4.2: Generate PDF Report
1. Click "Bericht generieren" (Generate Report) button
2. Wait for generation (may take longer than HTML)
3. Verify success message
4. Note output file path

**✓ Expected Results**:
- PDF generation completes without errors
- Success message displayed
- PDF file created at specified location
- File size reasonable (> 50 KB)

#### Step 4.3: Verify PDF Report Content
1. Open the generated PDF in a PDF reader
2. Verify the following:

**General PDF Properties**:
- [ ] PDF opens without errors
- [ ] Page size is A4
- [ ] Margins are appropriate (2cm)
- [ ] Text is searchable (not rasterized)
- [ ] Multiple pages if needed (no content cutoff)

**Content Verification**:
- [ ] All sections from HTML report are present
- [ ] Header with project name and date
- [ ] Project summary section
- [ ] Statistical analysis
- [ ] Site ranking table
- [ ] Site comparison
- [ ] Individual site details (all 3 sites)
- [ ] Cost breakdown
- [ ] Footer

**Formatting Verification**:
- [ ] Colors preserved from HTML
- [ ] Tables properly formatted
- [ ] Text readable (appropriate font size)
- [ ] No overlapping content
- [ ] Page breaks logical (not mid-table)
- [ ] Numbers formatted with proper decimals

**✓ Expected Results**: PDF matches HTML content, professional formatting, all data visible

### Phase 5: Excel Report Generation

#### Step 5.1: Configure Excel Export
1. In format dropdown, select "Excel Spreadsheet"
2. Click "Browse" button
3. Choose output location and filename (e.g., `multi_site_report.xlsx`)
4. Ensure same cost parameters
5. Ensure all 3 sites selected

**✓ Expected Results**:
- Format changes to Excel
- File browser shows .xlsx filter
- Output path updates

#### Step 5.2: Generate Excel Report
1. Click "Bericht generieren" button
2. Wait for generation
3. Verify success message
4. Note output path

**✓ Expected Results**:
- Excel generation completes without errors
- Success message displayed
- .xlsx file created
- File size reasonable (> 10 KB)

#### Step 5.3: Verify Excel Report - Summary Sheet
1. Open the Excel file in Excel or LibreOffice Calc
2. Navigate to "Summary" sheet (first sheet)
3. Verify the following:

**Sheet Structure**:
- [ ] Sheet name is "Summary"
- [ ] Title: "Multi-Site Erdmassenvergleich"
- [ ] Project name displayed
- [ ] Creation timestamp

**Project Scope Section**:
- [ ] Anzahl Standorte (Number of sites): 3
- [ ] Gesamtkosten (Total costs): calculated correctly
- [ ] Durchschnittliche Kosten pro Standort (Avg cost per site)

**Volume Overview Table**:
- [ ] Gesamt Abtrag (Total cut)
- [ ] Gesamt Auftrag (Total fill)
- [ ] Gesamt Erdbewegungen (Total earthwork)
- [ ] Netto-Bilanz (Net balance)
- [ ] Externes Schottermaterial (External gravel)
- [ ] Values match sum of individual sites

**Statistical Analysis Section**:
- [ ] Cut statistics (average, min, max)
- [ ] Fill statistics (average, min, max)
- [ ] Values calculated correctly

**Formatting**:
- [ ] Table headers: blue background (#667EEA), white text, bold
- [ ] Numbers formatted with thousand separators
- [ ] Columns properly sized
- [ ] Arial font throughout

**✓ Expected Results**: All data accurate, formatting professional

#### Step 5.4: Verify Excel Report - Sites Ranking Sheet
1. Navigate to "Sites Ranking" sheet (second sheet)
2. Verify the following:

**Sheet Structure**:
- [ ] Sheet name is "Sites Ranking"
- [ ] Title: "Standort-Rangliste nach Komplexität"

**Ranking Order**:
- [ ] Sites sorted by total earthwork (descending)
- [ ] Rank 1: High complexity site (highest volume)
- [ ] Rank 2: Medium complexity site
- [ ] Rank 3: Low complexity site (lowest volume)

**Table Columns**:
- [ ] Rang (Rank): 1, 2, 3
- [ ] Standort (Site name)
- [ ] Gesamt Erdbewegungen (Total earthwork)
- [ ] Abtrag (Cut)
- [ ] Auftrag (Fill)
- [ ] Kranstellflächen-Höhe (Crane height)
- [ ] Kosten (geschätzt) (Estimated cost)

**Color Coding**:
- [ ] High complexity: red tint (#FFEBEE)
- [ ] Medium complexity: orange tint (#FFF3E0)
- [ ] Low complexity: green tint (#E8F5E9)

**Formatting**:
- [ ] Headers: blue background, white text
- [ ] Numbers properly formatted
- [ ] Columns sized appropriately

**✓ Expected Results**: Correct ranking order, accurate data, proper color coding

#### Step 5.5: Verify Excel Report - Individual Sites Sheet
1. Navigate to "Individual Sites" sheet (third sheet)
2. Verify the following:

**Sheet Structure**:
- [ ] Sheet name is "Individual Sites"
- [ ] Title: "Detaillierte Standort-Einzelauswertung"

**For Each of the 3 Sites, Verify**:

**Site Header**:
- [ ] Site name with 📍 icon
- [ ] Standortkoordinaten (Coordinates)
- [ ] Kranstellflächen-Höhe (Crane height)
- [ ] Geschätzte Gesamtkosten (Total costs)

**Volume Overview Table**:
- [ ] Abtrag (Cut volume)
- [ ] Auftrag (Fill volume)
- [ ] Gesamt bewegt (Total moved)
- [ ] Netto-Bilanz (Net balance)
- [ ] Externes Schottermaterial (External gravel)

**Terrain Statistics Table**:
- [ ] Min Höhe (Minimum height)
- [ ] Max Höhe (Maximum height)
- [ ] Mittlere Höhe (Mean height)
- [ ] Höhenbereich (Height range)

**Cost Breakdown Table**:
- [ ] Abtrag (Cut) - volume, unit price, total
- [ ] Auftrag (Fill) - volume, unit price, total
- [ ] Schottermaterial (Gravel) - volume, unit price, total
- [ ] Transport - distance, cost
- [ ] Gesamtkosten (Total) - highlighted row

**Formatting**:
- [ ] Headers: blue background
- [ ] Total row: gray background
- [ ] Numbers: appropriate formats
- [ ] Columns properly sized

**✓ Expected Results**: All 3 sites present, complete data, proper formatting

### Phase 6: Data Accuracy Verification

#### Step 6.1: Verify Volume Totals
1. Open all three report formats side by side
2. For each site, verify cut and fill volumes match across:
   - HTML report
   - PDF report
   - Excel report (Individual Sites sheet)
3. Verify total project volumes in Summary sections match sum of individual sites

**Calculation Check**:
```
Total Cut = Site1.Cut + Site2.Cut + Site3.Cut
Total Fill = Site1.Fill + Site2.Fill + Site3.Fill
Total Earthwork = Total Cut + Total Fill
Net Balance = Total Cut - Total Fill
```

**✓ Expected Results**: All volume calculations accurate, consistent across formats

#### Step 6.2: Verify Cost Calculations
1. Verify cost breakdown in each report format
2. Check cost calculations:

```
Site Cost = (Cut Volume × Cut Unit Cost) +
            (Fill Volume × Fill Unit Cost) +
            (Gravel Volume × Gravel Unit Cost) +
            Transport Cost

Total Project Cost = Site1.Cost + Site2.Cost + Site3.Cost
```

3. Verify costs match across all formats
4. Verify cost parameters used are consistent

**✓ Expected Results**: Cost calculations accurate, consistent across formats

#### Step 6.3: Verify Site Rankings
1. In all three formats, check Site Ranking section
2. Verify sites are ranked by total earthwork volume (cut + fill)
3. Verify ranking order:
   - Rank 1: Highest earthwork volume
   - Rank 2: Medium earthwork volume
   - Rank 3: Lowest earthwork volume

**Verification**:
```
For each site: Total Earthwork = Cut Volume + Fill Volume
Rank by Total Earthwork in descending order
```

**✓ Expected Results**: Ranking consistent across all formats, ordered correctly

#### Step 6.4: Verify Statistical Calculations
1. Check statistical analysis sections in all formats
2. Verify calculations:

**Cut Statistics**:
- Average = (Site1.Cut + Site2.Cut + Site3.Cut) / 3
- Minimum = min(Site1.Cut, Site2.Cut, Site3.Cut)
- Maximum = max(Site1.Cut, Site2.Cut, Site3.Cut)

**Fill Statistics**:
- Average = (Site1.Fill + Site2.Fill + Site3.Fill) / 3
- Minimum = min(Site1.Fill, Site2.Fill, Site3.Fill)
- Maximum = max(Site1.Fill, Site2.Fill, Site3.Fill)

**✓ Expected Results**: Statistical values correct, consistent across formats

### Phase 7: Edge Cases and Error Handling

#### Step 7.1: Test with No Sites Selected
1. Return to Multi-Site Report tab
2. Click "Deselect All"
3. Click "Generate Report"

**✓ Expected Result**: Appropriate error message displayed (e.g., "Please select at least one site")

#### Step 7.2: Test with Only One Site
1. Select only one site checkbox
2. Generate report in HTML format
3. Open and verify report

**✓ Expected Results**:
- Report generates successfully
- Statistics show single site data
- Ranking shows single site
- No division by zero errors

#### Step 7.3: Test with Missing Output Path
1. Select all 3 sites
2. Clear the output path field
3. Click "Generate Report"

**✓ Expected Result**: Default path is created OR appropriate error message

#### Step 7.4: Test Invalid Cost Parameters
1. Enter negative value for cut cost
2. Attempt to generate report

**✓ Expected Result**: Validation error OR parameter corrected to positive value

### Phase 8: User Experience Verification

#### Step 8.1: Verify Report Opens Automatically
After generating each report format, verify:
- [ ] HTML opens in default web browser
- [ ] PDF opens in default PDF viewer
- [ ] Excel opens in default spreadsheet application

**✓ Expected Result**: Reports open automatically without manual intervention

#### Step 8.2: Verify Progress Feedback
During report generation:
- [ ] Status message or progress indicator visible
- [ ] UI remains responsive (or shows wait cursor)
- [ ] Success message appears when complete

**✓ Expected Result**: User receives clear feedback during process

#### Step 8.3: Verify Error Messages
If errors occur:
- [ ] Error messages are user-friendly (German language)
- [ ] Errors indicate what went wrong
- [ ] Errors suggest corrective action if applicable

**✓ Expected Result**: Error handling is professional and helpful

## Test Completion Checklist

### Critical Verification Points
- [ ] All 3 sites processed successfully with different terrain complexity
- [ ] Multi-Site Report tab accessible and functional
- [ ] Site selection checkbox list displays all processed sites
- [ ] HTML report generates and contains all required sections
- [ ] PDF report generates and matches HTML content
- [ ] Excel report generates with 3 sheets containing correct data
- [ ] Sites ranked by earthwork volume in descending order
- [ ] Total costs and volumes match sum of individual sites
- [ ] All report formats are consistent and accurate
- [ ] Reports open automatically after generation
- [ ] User interface is intuitive and error-free

### Data Accuracy Verification
- [ ] Volume calculations correct across all formats
- [ ] Cost calculations consistent and accurate
- [ ] Statistical analysis values correct
- [ ] Ranking order based on earthwork volume
- [ ] No missing or corrupted data

### Quality Standards
- [ ] Professional formatting in all report types
- [ ] German language labels throughout
- [ ] Consistent styling and branding
- [ ] Numbers formatted with appropriate precision
- [ ] Tables and charts clearly readable

## Expected Test Duration
- **Phase 1-2 (Setup & Processing)**: 15-20 minutes
- **Phase 3-5 (Report Generation)**: 15-20 minutes
- **Phase 6 (Data Verification)**: 10-15 minutes
- **Phase 7-8 (Edge Cases & UX)**: 10-15 minutes
- **Total**: 50-70 minutes

## Troubleshooting

### Plugin Doesn't Load
- Check QGIS Python console for errors
- Verify plugin files are in correct directory
- Try restarting QGIS

### Calculations Fail
- Verify terrain raster layer is valid
- Check that point is within raster bounds
- Ensure CRS is properly configured

### Multi-Site Tab Not Visible
- Verify plugin version includes multi-site feature
- Check for UI initialization errors in logs
- Try reopening the plugin dialog

### Report Generation Fails
- **HTML**: Check write permissions on output directory
- **PDF**: Verify weasyprint is installed (`pip install weasyprint>=56.0`)
- **Excel**: Verify openpyxl is installed (`pip install openpyxl>=3.0.0`)

### Reports Don't Open Automatically
- Manually navigate to output directory
- Check system file associations for .html, .pdf, .xlsx
- Verify QDesktopServices is working

### Data Doesn't Match
- Re-run calculations for affected sites
- Clear processed sites and start fresh
- Check QGIS log for calculation warnings

## Success Criteria

The test is successful when:

1. ✅ **Functionality**: All features work as designed
   - Site processing completes without errors
   - All report formats generate successfully
   - Reports contain accurate, complete data

2. ✅ **Accuracy**: Data is consistent and correct
   - Volume calculations match across formats
   - Cost calculations are accurate
   - Rankings based on correct criteria
   - Statistics calculated properly

3. ✅ **Quality**: Reports are professional
   - Formatting is clean and readable
   - Styling is consistent
   - Content is well-organized
   - No layout issues or errors

4. ✅ **Usability**: User experience is smooth
   - UI is intuitive and responsive
   - Reports open automatically
   - Error messages are helpful
   - Process is efficient

## Test Report Template

```
TEST EXECUTION REPORT
=====================

Test Date: __________
Tester Name: __________
QGIS Version: __________
Plugin Version: __________

RESULTS:
[ ] PASS  [ ] FAIL  [ ] PARTIAL

Sites Tested:
1. ________ (Complexity: _____)
2. ________ (Complexity: _____)
3. ________ (Complexity: _____)

Report Formats Generated:
[ ] HTML  [ ] PDF  [ ] Excel

Critical Issues Found: __________

Minor Issues Found: __________

Data Accuracy: [ ] Verified  [ ] Issues Found

Notes:
__________________________________________
__________________________________________
__________________________________________

Recommendation: [ ] Approve  [ ] Reject  [ ] Revise
```

## References

- Spec: `.auto-claude/specs/003-multi-site-comparison-report/spec.md`
- Implementation Plan: `.auto-claude/specs/003-multi-site-comparison-report/implementation_plan.json`
- PDF Verification: `MANUAL_PDF_VERIFICATION.md`
- Excel Verification: `MANUAL_EXCEL_VERIFICATION.md`

---

**Note**: This is a comprehensive manual test that should be performed by a human tester with access to QGIS. The test validates the complete multi-site comparison report workflow from start to finish.
