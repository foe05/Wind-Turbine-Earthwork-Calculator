# Manual Excel Export Verification

This document provides instructions for manually verifying the Excel export functionality for multi-site reports.

## Prerequisites

Ensure the following dependencies are installed in your QGIS Python environment:
- `openpyxl>=3.0.0`

## Verification Steps

### 1. Create Test Data

```python
from windturbine_earthwork_calculator_v2.core.multi_site_report_generator import MultiSiteReportGenerator

# Create test data with 3 sites
test_sites = [
    {
        'site_id': 'WEA-01',
        'site_name': 'Windenergie Anlage 01',
        'coordinates': (3450000, 5750000),
        'results': {
            'total_cut': 2500.5,
            'total_fill': 1800.3,
            'net_volume': 700.2,
            'gravel_fill_external': 450.0,
            'crane_height': 425.5,
            'terrain_min': 420.0,
            'terrain_max': 435.0,
            'terrain_mean': 427.5,
            'total_platform_area': 2500.0,
            'total_area': 4500.0,
        },
        'config': {
            'slope_angle': 45.0,
        }
    },
    {
        'site_id': 'WEA-02',
        'site_name': 'Windenergie Anlage 02',
        'coordinates': (3451000, 5751000),
        'results': {
            'total_cut': 3200.0,
            'total_fill': 2100.0,
            'net_volume': 1100.0,
            'gravel_fill_external': 600.0,
            'crane_height': 445.2,
            'terrain_min': 438.0,
            'terrain_max': 455.0,
            'terrain_mean': 446.5,
            'total_platform_area': 2500.0,
            'total_area': 4500.0,
        },
        'config': {
            'slope_angle': 45.0,
        }
    },
    {
        'site_id': 'WEA-03',
        'site_name': 'Windenergie Anlage 03',
        'coordinates': (3452000, 5749000),
        'results': {
            'total_cut': 1500.0,
            'total_fill': 1300.0,
            'net_volume': 200.0,
            'gravel_fill_external': 300.0,
            'crane_height': 410.0,
            'terrain_min': 405.0,
            'terrain_max': 418.0,
            'terrain_mean': 411.5,
            'total_platform_area': 2500.0,
            'total_area': 4500.0,
        },
        'config': {
            'slope_angle': 45.0,
        }
    },
]

# Create report generator
generator = MultiSiteReportGenerator(test_sites)

# Generate Excel report
generator.generate_excel('/tmp/test_multi_site_report.xlsx', project_name='Test Windpark')

print("Excel report generated: /tmp/test_multi_site_report.xlsx")
```

### 2. Open and Verify Excel File

Open the generated Excel file `/tmp/test_multi_site_report.xlsx` and verify the following:

#### Summary Sheet
- [ ] Sheet name is "Summary"
- [ ] Title: "Multi-Site Erdmassenvergleich"
- [ ] Project name is displayed
- [ ] Creation timestamp is present
- [ ] Projektumfang section shows:
  - [ ] Anzahl Standorte: 3
  - [ ] Gesamtkosten (geschätzt): calculated value
  - [ ] Durchschnittliche Kosten pro Standort: calculated value
- [ ] Volumenübersicht table contains:
  - [ ] Gesamt Abtrag
  - [ ] Gesamt Auftrag
  - [ ] Gesamt Erdbewegungen
  - [ ] Netto-Bilanz
  - [ ] Externes Schottermaterial
- [ ] Statistische Auswertung section shows:
  - [ ] Abtrag-Statistik (Durchschnitt, Minimum, Maximum)
  - [ ] Auftrag-Statistik (Durchschnitt, Minimum, Maximum)
- [ ] Table headers have blue background (#667EEA)
- [ ] Numbers are formatted with thousand separators
- [ ] Columns are properly sized

#### Sites Ranking Sheet
- [ ] Sheet name is "Sites Ranking"
- [ ] Title: "Standort-Rangliste nach Komplexität"
- [ ] Sites are sorted by total earthwork volume (highest first)
- [ ] Expected order: WEA-02 (5300 m³), WEA-01 (4300.8 m³), WEA-03 (2800 m³)
- [ ] Table columns include:
  - [ ] Rang (1, 2, 3)
  - [ ] Standort name
  - [ ] Gesamt Erdbewegungen
  - [ ] Abtrag
  - [ ] Auftrag
  - [ ] Kranstellflächen-Höhe
  - [ ] Kosten (geschätzt)
- [ ] Rows have color coding:
  - [ ] High complexity: red tint (#FFEBEE)
  - [ ] Medium complexity: orange tint (#FFF3E0)
  - [ ] Low complexity: green tint (#E8F5E9)
- [ ] Table headers have blue background
- [ ] Numbers are formatted appropriately

#### Individual Sites Sheet
- [ ] Sheet name is "Individual Sites"
- [ ] Title: "Detaillierte Standort-Einzelauswertung"
- [ ] All 3 sites are present with detailed sections
- [ ] For each site, verify:
  - [ ] Site name with 📍 icon
  - [ ] Standortkoordinaten
  - [ ] Kranstellflächen-Höhe
  - [ ] Geschätzte Gesamtkosten
  - [ ] Volumenübersicht table (5 rows: Abtrag, Auftrag, Gesamt, Netto, Schotter)
  - [ ] Geländestatistik table (4 rows: min, max, mean, range)
  - [ ] Kostenaufschlüsselung table with:
    - [ ] Abtrag costs
    - [ ] Auftrag costs
    - [ ] Schottermaterial costs
    - [ ] Transport costs
    - [ ] Gesamtkosten (total row with gray background)
- [ ] Numbers are formatted correctly
- [ ] Columns are properly sized

### 3. Verify Data Accuracy

- [ ] Total volumes in Summary match sum of individual site volumes
- [ ] Ranking order matches expected order based on total earthwork
- [ ] Cost calculations are consistent across sheets
- [ ] Statistical values (avg, min, max) are correct

### 4. Verify Formatting

- [ ] All fonts are Arial
- [ ] Headers use proper styling (bold, white text, blue background)
- [ ] Numbers use appropriate formats (#,##0 for volumes, 0.00 for heights, #,##0 € for costs)
- [ ] Column widths are readable
- [ ] No overlapping text or truncated values

## Expected Results

After verification, all checkboxes should be checked. The Excel file should contain:
1. **Summary sheet**: Project-wide statistics and aggregations
2. **Sites Ranking sheet**: Sites sorted by complexity with color coding
3. **Individual Sites sheet**: Detailed breakdown for each site

All data should be properly formatted and readable in Excel or LibreOffice Calc.

## Troubleshooting

### Missing openpyxl module
```bash
pip install openpyxl>=3.0.0
```

### Import errors
Make sure the QGIS Python environment can access the plugin modules.

### File not generated
Check write permissions for the output directory and verify the logger output for errors.
