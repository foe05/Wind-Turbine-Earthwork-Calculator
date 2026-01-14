# Performance Testing Guide

## Overview

This document describes the performance testing requirements and procedures for the Enhanced PDF Report Generation feature.

**Performance Requirement**: PDF generation must complete within **10 seconds** for a standard WKA report with all features enabled.

## Standard Report Configuration

A "standard report" is defined as:
- **3 wind turbine sites**
- **5 height scenarios per site** (for comparison table)
- **All charts enabled** (volume charts, comparison charts)
- **Company logo** included in header
- **Custom branding** (company name and footer text)
- **Comparison tables** showing all scenarios side-by-side

## Performance Test Options

### Option 1: Automated Integration Test (Recommended)

The integration test suite includes a comprehensive performance test:

```bash
# From report_service directory
python3 -m pytest tests/test_integration_pdf.py::TestIntegrationPerformance::test_standard_report_performance -v -s
```

Or using unittest:

```bash
python3 -m unittest tests.test_integration_pdf.TestIntegrationPerformance.test_standard_report_performance -v
```

**Output**: The test will print detailed timing information and a PASS/FAIL result based on the 10-second threshold.

### Option 2: Manual Performance Test Script

A standalone script is provided for manual testing:

```bash
# From report_service directory
python3 tests/manual_performance_test.py
```

This script:
1. Creates a standard report configuration (3 sites, 5 scenarios each)
2. Generates HTML report
3. Converts to PDF
4. Measures and reports timing for each step
5. Compares against the 10-second target
6. Displays detailed metrics and file sizes

### Option 3: API-Based Performance Test

Test via the REST API:

```bash
# Start the service
uvicorn app.main:app --reload --host 0.0.0.0 --port 8005

# In another terminal, use curl with timing
time curl -X POST http://localhost:8005/api/reports/generate \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/standard_report_request.json \
  -o /tmp/test_report.pdf
```

## Prerequisites

Before running performance tests, ensure all dependencies are installed:

```bash
# Create virtual environment (if not already created)
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# For running pytest
pip install pytest
```

## Expected Results

### Timing Breakdown

Based on optimizations implemented in subtask-5-3:

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| Chart generation | 1-2s | Matplotlib with DPI=100, optimized rendering |
| Template rendering | 0.5-1s | Jinja2 HTML generation with charts/branding |
| PDF conversion | 3-5s | WeasyPrint HTML→PDF conversion |
| Branding processing | <0.1s | Logo validation and processing |
| **TOTAL** | **5-8s** | Well under 10s target |

### Performance Metrics

The tests measure and report:
- **HTML generation time** - Time to render Jinja2 template with all data
- **PDF conversion time** - Time for WeasyPrint to convert HTML to PDF
- **Total generation time** - End-to-end time from request to PDF file
- **File sizes** - HTML and PDF output file sizes

### Performance Optimizations

The following optimizations were implemented to achieve <10s generation:

1. **Chart Rendering** (subtask-5-3):
   - DPI reduced from 150 to 100 (33% faster)
   - Removed `bbox_inches='tight'` (15-20% faster)
   - Matplotlib performance rcParams configuration
   - Simplified chart styling

2. **Template Rendering**:
   - Conditional chart generation (only when data available)
   - Optimized CSS print styles
   - Efficient Jinja2 template structure

3. **PDF Conversion**:
   - Optimized page break controls
   - Efficient image embedding (base64 data URIs)
   - Minimal external resource loading

## Interpreting Results

### PASS Criteria
- Total generation time < 10 seconds
- PDF file generated successfully
- All features present (charts, branding, comparison tables)
- PDF file size reasonable (<5 MB for standard report)

### FAIL Criteria
- Total generation time ≥ 10 seconds
- Generation errors or exceptions
- Missing features in output
- Excessive file size (>10 MB)

### Performance Warnings

If generation time is between 8-10 seconds:
- ⚠️ **Warning**: Close to threshold, may exceed on slower hardware
- Consider additional optimizations
- Test on production-equivalent hardware

If generation time is >10 seconds:
- ❌ **Failure**: Does not meet acceptance criteria
- Review optimization opportunities
- Check for performance regressions
- Verify hardware meets minimum requirements

## Troubleshooting

### Test Skipped
```
OK (skipped=1) - Dependencies not available
```

**Solution**: Install required dependencies:
```bash
pip install weasyprint matplotlib Pillow
```

### Slow Performance (>10s)

**Possible causes**:
1. **Hardware constraints** - Test on production-equivalent hardware
2. **Missing optimizations** - Verify subtask-5-3 optimizations are applied
3. **Large data sets** - Verify using standard configuration (3 sites, 5 scenarios)
4. **I/O bottlenecks** - Check disk performance, use SSD if available

**Debug steps**:
1. Check individual timing breakdowns (HTML vs PDF)
2. Run with Python profiler: `python3 -m cProfile tests/manual_performance_test.py`
3. Review logs for performance warnings
4. Verify matplotlib backend is set to 'Agg' (non-interactive)

### Memory Issues

If tests fail with memory errors:
- Reduce chart DPI (currently 100, can go lower if needed)
- Ensure charts are closed after generation
- Check for memory leaks in generator code

## Hardware Requirements

**Minimum specifications for <10s generation**:
- CPU: 2 cores, 2.0 GHz or faster
- RAM: 2 GB available
- Disk: SSD recommended (HDD may be slower)
- Python: 3.9 or later

**Recommended specifications**:
- CPU: 4+ cores, 2.5 GHz or faster
- RAM: 4+ GB available
- Disk: SSD
- Python: 3.11 or later

## Continuous Integration

For CI/CD pipelines:

```yaml
# Example GitHub Actions snippet
- name: Performance Test
  run: |
    cd webapp/services/report_service
    source venv/bin/activate
    python3 -m pytest tests/test_integration_pdf.py::TestIntegrationPerformance -v

- name: Check Performance Results
  run: |
    # Parse test output and fail if performance threshold exceeded
    # (Implement based on your CI system)
```

## Related Files

- `tests/test_integration_pdf.py` - Integration test suite with performance tests
- `tests/manual_performance_test.py` - Standalone manual performance test script
- `app/core/generator.py` - Report generator with performance optimizations
- `app/core/chart_generator.py` - Optimized chart generation module
- `.auto-claude/specs/002-enhanced-pdf-report-generation/OPTIMIZATION_SUMMARY.md` - Detailed optimization summary

## References

- Acceptance Criterion: "PDF generation completes within 10 seconds for standard reports" (spec.md line 19)
- Subtask 5-3: Performance optimizations implementation
- Subtask 7-2: Performance testing verification (this document)
