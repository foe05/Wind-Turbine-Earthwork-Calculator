# Visual QA Checklist - Enhanced PDF Reports

This document provides a comprehensive checklist for manually verifying the visual quality of generated PDF reports.

## Overview

The enhanced PDF report generation feature adds:
- Embedded charts for cut/fill volume visualizations
- Comparison tables for multiple height scenarios
- Customizable branding (logo, company name, custom footer)
- Optimized page breaks for professional output

## Test Files

Run the Visual QA test script to generate sample PDFs:

```bash
cd webapp/services/report_service
python3 tests/visual_qa_test.py
```

This generates the following test PDFs in `tests/visual_qa_output/`:

1. **visual_qa_complete.pdf** - Full featured report (all enhancements)
2. **visual_qa_minimal.pdf** - Basic report (no scenarios, no branding)
3. **visual_qa_multi_site.pdf** - Multiple sites (5 sites) for page break testing
4. **visual_qa_no_branding.pdf** - Report without branding
5. **visual_qa_no_scenarios.pdf** - Report without comparison tables

## Visual QA Checklist

### 1. Charts Quality ✓

**Files to check:** `visual_qa_complete.pdf`, `visual_qa_multi_site.pdf`

- [ ] **Chart Rendering**
  - Charts are rendered clearly (not pixelated or blurry)
  - Charts are at appropriate resolution for print and screen
  - Charts are embedded inline (not as external references)

- [ ] **Chart Labeling**
  - X-axis and Y-axis have clear labels
  - Axis labels are readable and not cut off
  - Units are displayed correctly (m³, €, etc.)
  - Chart titles are descriptive and accurate

- [ ] **Chart Legend**
  - Legend is visible and positioned appropriately
  - Legend entries match chart elements
  - Colors in legend match chart colors
  - Legend text is readable

- [ ] **Chart Colors**
  - Colors are distinct and professional
  - Color scheme is consistent across all charts
  - Cut volumes use red/accent color
  - Fill volumes use green/success color
  - Colors print well (not too light or dark)

- [ ] **Chart Types**
  - Volume bar charts display correctly
  - Comparison charts show multiple sites clearly
  - Pie charts (if any) have clear segment labels
  - All chart types are appropriate for the data

- [ ] **Chart Sizing**
  - Charts are appropriately sized (not too small or large)
  - Charts maintain aspect ratio
  - Multiple charts on same page are balanced
  - Charts don't overlap with other content

### 2. Comparison Table Quality ✓

**Files to check:** `visual_qa_complete.pdf`, `visual_qa_multi_site.pdf`

- [ ] **Table Structure**
  - Table is properly formatted with clear borders
  - All columns are aligned correctly
  - Column headers are bold and centered
  - Row data is centered in cells

- [ ] **Table Content**
  - All scenario heights are displayed correctly
  - Cut and fill volumes are accurate
  - Total costs are formatted properly
  - All numbers have appropriate decimal places

- [ ] **Optimal Scenario Highlighting**
  - Optimal scenario row has green background (#E8F5E9)
  - Optimal scenario row has bold text
  - "OPTIMAL" badge is visible and styled correctly
  - Badge color (green) matches success color scheme
  - Only one scenario per site is marked as optimal

- [ ] **Table Readability**
  - Font size is readable (not too small)
  - Text doesn't overflow cells
  - Numbers are properly aligned (right-aligned or centered)
  - German labels are correct ("Plattform-Höhe", "Aushub", etc.)

- [ ] **Table Position**
  - Table appears after volume data for each site
  - Table has proper spacing above and below
  - Table doesn't overlap with other content
  - Section heading is clear

### 3. Branding Quality ✓

**Files to check:** `visual_qa_complete.pdf`, `visual_qa_multi_site.pdf`
**Comparison file:** `visual_qa_no_branding.pdf` (should have no branding)

- [ ] **Logo Display**
  - Logo appears in header section
  - Logo is properly sized (max 200px width, 80px height on screen)
  - Logo is properly sized for print (max 60px height in PDF)
  - Logo maintains aspect ratio (not stretched)
  - Logo is centered or properly aligned
  - Logo image quality is good (not pixelated)

- [ ] **Company Name**
  - Company name appears above report title
  - Company name uses primary color styling
  - Company name font size is appropriate (16px)
  - Company name is properly positioned
  - Company name has adequate spacing

- [ ] **Custom Footer**
  - Custom footer text appears at bottom of pages
  - Footer text is readable and properly styled
  - Footer text doesn't overflow or wrap awkwardly
  - Footer includes timestamp if specified
  - Footer text is centered

- [ ] **Branding Consistency**
  - All branding elements use consistent styling
  - Branding doesn't interfere with main content
  - Branding appears professional and polished
  - Default footer is shown when no custom footer provided

- [ ] **No Branding Fallback**
  - Reports without branding still look professional
  - Default header and footer work correctly
  - No broken images or missing elements

### 4. Page Break Quality ✓

**Files to check:** `visual_qa_multi_site.pdf` (best for testing page breaks)

- [ ] **Chart Page Breaks**
  - Charts are not split across pages
  - Chart title stays with chart image
  - Chart description stays with chart
  - Multiple charts on same page are balanced

- [ ] **Table Page Breaks**
  - Tables are not split across pages (volume tables, comparison tables)
  - Table headers stay with table content
  - Table rows are not split awkwardly
  - Material balance section stays together

- [ ] **Site Card Page Breaks**
  - Each site card stays together when possible
  - Site header stays with site body content
  - Site sections don't split awkwardly
  - Adequate spacing between sites

- [ ] **Section Page Breaks**
  - Summary cards section stays together
  - Charts section stays together when possible
  - Material balance section doesn't split
  - Comparison table section doesn't split

- [ ] **Header/Footer Page Breaks**
  - Report header doesn't have page break after it
  - Footer stays at bottom of pages
  - Header doesn't repeat inappropriately
  - Page break controls work correctly

- [ ] **Overall Flow**
  - Page breaks feel natural and professional
  - No orphaned content (single line at page break)
  - Content density is appropriate (not too cramped)
  - White space is used effectively

### 5. Overall Layout Quality ✓

**Files to check:** All test PDFs

- [ ] **Professional Appearance**
  - Report looks polished and professional
  - Color scheme is consistent throughout
  - Typography is clean and readable
  - Visual hierarchy is clear

- [ ] **Spacing and Alignment**
  - Consistent spacing between sections
  - Elements are properly aligned
  - Margins are consistent on all pages
  - Padding is appropriate around content

- [ ] **Font Sizing**
  - Main text is readable (14px body text)
  - Headers have appropriate hierarchy (36px h1, 20px h2, 16px h3)
  - Small text (labels, units) is still readable
  - Font sizes are consistent with design

- [ ] **Content Organization**
  - Logical flow from summary → charts → site details
  - Related content is grouped together
  - Section transitions are clear
  - Navigation through report is intuitive

- [ ] **No Overlapping Content**
  - No text overlaps with other text
  - Images don't overlap with text
  - Tables don't overlap with other elements
  - All content is clearly separated

- [ ] **Print Quality**
  - Report looks good when printed
  - Colors are print-friendly
  - Text is crisp and clear
  - Images maintain quality in print

- [ ] **Responsive Elements**
  - Summary cards layout adapts appropriately
  - Charts scale to fit page width
  - Tables fit within page margins
  - Content doesn't overflow page boundaries

### 6. Edge Cases ✓

**Files to check:** `visual_qa_minimal.pdf`, `visual_qa_no_scenarios.pdf`, `visual_qa_no_branding.pdf`

- [ ] **Minimal Data Handling**
  - Report with minimal data still looks good
  - No broken sections or missing content
  - Appropriate messages for missing data
  - Layout adapts to less content

- [ ] **Missing Scenarios**
  - Report without scenarios doesn't show empty comparison table
  - Other sections still display correctly
  - No JavaScript errors or broken references

- [ ] **Missing Branding**
  - Report without branding uses default header/footer
  - No broken image placeholders
  - Default styling is professional

- [ ] **Single vs Multiple Sites**
  - Single site reports look complete
  - Multiple site reports maintain consistency
  - Comparison charts appear only for multi-site reports
  - Site numbering is correct

## Test Results Template

Use this template to document your Visual QA results:

```
## Visual QA Test Results

**Date:** [YYYY-MM-DD]
**Tester:** [Name]
**Test Files Generated:** [Yes/No]

### 1. Charts Quality
- Overall Rating: [Pass/Fail/Needs Improvement]
- Issues Found: [List any issues]
- Notes: [Additional observations]

### 2. Comparison Table Quality
- Overall Rating: [Pass/Fail/Needs Improvement]
- Issues Found: [List any issues]
- Notes: [Additional observations]

### 3. Branding Quality
- Overall Rating: [Pass/Fail/Needs Improvement]
- Issues Found: [List any issues]
- Notes: [Additional observations]

### 4. Page Break Quality
- Overall Rating: [Pass/Fail/Needs Improvement]
- Issues Found: [List any issues]
- Notes: [Additional observations]

### 5. Overall Layout Quality
- Overall Rating: [Pass/Fail/Needs Improvement]
- Issues Found: [List any issues]
- Notes: [Additional observations]

### 6. Edge Cases
- Overall Rating: [Pass/Fail/Needs Improvement]
- Issues Found: [List any issues]
- Notes: [Additional observations]

### Final Verdict
- [ ] All checks passed - Ready for production
- [ ] Minor issues found - Can be addressed in follow-up
- [ ] Major issues found - Requires immediate attention

### Screenshots
[Attach screenshots of any issues found]

### Recommendations
[List any recommendations for improvements]
```

## Common Issues and Solutions

### Issue: Charts are pixelated
- **Cause:** DPI setting too low
- **Check:** `chart_generator.py` DPI parameter (should be 100-150)
- **Solution:** Increase DPI in chart generation

### Issue: Comparison table not highlighting optimal scenario
- **Cause:** CSS not applied or `is_optimal` flag not set
- **Check:** Template CSS and data structure
- **Solution:** Verify `is_optimal: true` in scenario data and CSS class

### Issue: Logo not appearing
- **Cause:** Invalid base64 encoding or logo validation failure
- **Check:** Generator logs for validation warnings
- **Solution:** Use valid PNG/JPEG, ensure proper base64 encoding

### Issue: Page breaks split content
- **Cause:** Print CSS not applied properly
- **Check:** `@media print` rules in template
- **Solution:** Add `page-break-inside: avoid` to affected elements

### Issue: Text overflow or overlap
- **Cause:** Content width exceeds container
- **Check:** Container widths and text wrapping
- **Solution:** Adjust CSS max-widths and word-wrap settings

## Approval

Once all checks are completed and any issues are resolved:

- [ ] Visual QA checklist completed
- [ ] Test results documented
- [ ] Screenshots collected (if issues found)
- [ ] Sign-off obtained

**Approved by:** ___________________
**Date:** ___________________
**Signature:** ___________________
