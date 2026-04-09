# Visual QA Testing - Quick Start Guide

## Overview

This directory contains infrastructure for Visual QA testing of enhanced PDF reports.

## Quick Start

### 1. Install Dependencies

```bash
cd webapp/services/report_service
pip install -r requirements.txt
```

### 2. Generate Test PDFs

```bash
python3 tests/visual_qa_test.py
```

This generates 5 test PDFs in `tests/visual_qa_output/`:
- `visual_qa_complete.pdf` - Full featured report
- `visual_qa_minimal.pdf` - Basic report
- `visual_qa_multi_site.pdf` - 5 sites (page break testing)
- `visual_qa_no_branding.pdf` - Without branding
- `visual_qa_no_scenarios.pdf` - Without comparison tables

### 3. Inspect PDFs

Open each PDF and use the checklist in `VISUAL_QA_CHECKLIST.md` to verify:
- Charts quality (clear, labeled, professional)
- Comparison tables (readable, optimal highlighting)
- Branding (logo, company name, footer)
- Page breaks (no awkward splits)
- Overall layout (professional, aligned, spaced)

### 4. Document Results

Use the template in `VISUAL_QA_CHECKLIST.md` to record your findings.

## Files

| File | Purpose |
|------|---------|
| `visual_qa_test.py` | Generate test PDFs with different configurations |
| `VISUAL_QA_CHECKLIST.md` | Comprehensive manual inspection checklist (50+ items) |
| `VISUAL_QA_RESULTS.md` | Infrastructure status and verification requirements |
| `README_VISUAL_QA.md` | This quick start guide |

## What to Check

### 1. Charts ✓
- Clear rendering (not pixelated)
- Proper labels and units
- Distinct colors
- Professional appearance

### 2. Comparison Table ✓
- Green highlighting for optimal scenario
- "OPTIMAL" badge visible
- Proper formatting and alignment
- All data displayed correctly

### 3. Branding ✓
- Logo appears and is properly sized
- Company name styled correctly
- Custom footer text visible
- Fallback works when branding absent

### 4. Page Breaks ✓
- Charts not split across pages
- Tables stay together
- Site cards don't break awkwardly
- Natural page flow

### 5. Layout ✓
- Professional appearance
- Consistent spacing
- Readable fonts
- No overlaps

## Expected Results

✅ **PASS Criteria:**
- All checklist items verified
- No visual defects or issues
- Performance <10s for standard report
- Professional output quality

⚠️ **Review Needed:**
- Minor formatting issues
- Performance slightly over target
- Edge cases need attention

❌ **FAIL Criteria:**
- Charts not rendering
- Tables split inappropriately
- Branding missing or broken
- Major layout issues

## Common Issues

| Issue | Check | Solution |
|-------|-------|----------|
| Charts pixelated | DPI setting | Increase DPI in chart_generator.py |
| Logo missing | Base64 encoding | Verify valid PNG/JPEG format |
| No highlighting | CSS/data flag | Check `is_optimal` flag and CSS |
| Content splits | Print CSS | Add `page-break-inside: avoid` |

## Performance Targets

- **Standard report (3 sites, 5 scenarios):** <10 seconds
- **File size:** <5MB for typical report
- **Chart resolution:** 100 DPI (good balance of quality/speed)

## Support

For issues or questions:
1. Check `VISUAL_QA_CHECKLIST.md` for detailed guidance
2. Review `VISUAL_QA_RESULTS.md` for expected behavior
3. Check implementation in `webapp/services/report_service/app/`

---

**Last Updated:** 2026-01-14
**Subtask:** subtask-7-3 - Visual QA verification
