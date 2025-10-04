"""
HTML Report Generator für Wind Turbine Earthwork Calculator
===========================================================

Professional White-Paper-Design mit PDF-Export und Geländeschnitt-Integration

VERSION: 1.0
DATUM: Oktober 2025
"""

import os
from datetime import datetime


class HTMLReportGenerator:
    """Generiert professionelle HTML-Reports im White-Paper-Design"""
    
    def __init__(self):
        self.version = "5.5"
    
    def create_report(self, results_list, output_path, project_name="Windpark-Projekt",
                     profile_output_folder=None, **kwargs):
        """
        Erstellt kompletten HTML-Report
        
        Args:
            results_list: Liste von Dicts mit Berechnungsergebnissen
            output_path: Pfad zur HTML-Ausgabedatei
            project_name: Name des Projekts
            profile_output_folder: Ordner mit Geländeschnitt-PNGs (optional)
            **kwargs: Zusätzliche Parameter (swell_factor, compaction_factor, etc.)
        
        Returns:
            str: Pfad zur erstellten HTML-Datei
        """
        # Meta-Daten (Feld-Namen aus prototype.py)
        total_sites = len(results_list)
        total_cut = sum(r.get('total_cut', 0) for r in results_list)
        total_fill = sum(r.get('total_fill', 0) for r in results_list)
        total_balance = total_cut - total_fill
        total_excavated = sum(r.get('excavated_volume', 0) for r in results_list)
        
        now = datetime.now()
        report_date = now.strftime('%d.%m.%Y')
        report_time = now.strftime('%H:%M')
        
        # HTML zusammensetzen
        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Erdarbeits-Bericht - {project_name}</title>
    
    <!-- Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
    
    <style>
        {self._get_report_css()}
    </style>
</head>
<body>
    <!-- PDF-Export-Button -->
    <div class="report-header">
        <button onclick="window.print()" class="pdf-export-btn">
            📄 Als PDF exportieren
        </button>
    </div>
    
    <!-- COVER PAGE -->
    {self._create_cover_page_html(project_name, total_sites, report_date, report_time)}
    
    <!-- EXECUTIVE SUMMARY -->
    {self._create_summary_page_html(total_sites, total_cut, total_fill, total_balance)}
    
    <!-- STANDORT-DETAILS -->
    {self._create_all_sites_html(results_list, profile_output_folder, output_path)}
    
    <!-- FOOTER -->
    {self._create_footer_html(report_date, report_time)}
    
    <!-- MODAL -->
    {self._create_modal_html()}
    
    <!-- JAVASCRIPT -->
    <script>
        {self._get_report_javascript()}
    </script>
</body>
</html>
"""
        
        # HTML-Datei schreiben
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        return output_path
    
    def _get_report_css(self):
        """Komplettes CSS für den Report"""
        return """
        /* CSS VARIABLEN */
        :root {
            --primary-dark: #2C3E50;
            --primary-blue: #34495E;
            --accent-pink: #E74C3C;
            --bg-white: #FFFFFF;
            --bg-light-gray: #F8F9FA;
            --bg-card: #FAFBFC;
            --text-dark: #2C3E50;
            --text-medium: #7F8C8D;
            --text-light: #BDC3C7;
            --border-light: #ECF0F1;
            --color-cut: #E74C3C;
            --color-fill: #27AE60;
            --color-process: #3498DB;
            --color-surplus: #F39C12;
            --color-deficit: #9B59B6;
        }
        
        /* GLOBAL */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: var(--text-dark);
            background: var(--bg-white);
        }
        
        /* TYPOGRAFIE */
        h1 {
            font-size: 42px;
            font-weight: 800;
            letter-spacing: -1px;
            line-height: 1.2;
            margin-bottom: 20px;
        }
        
        h2 {
            font-size: 32px;
            font-weight: 700;
            margin-top: 40px;
            margin-bottom: 20px;
            color: var(--primary-dark);
        }
        
        h3 {
            font-size: 24px;
            font-weight: 600;
            margin-top: 30px;
            margin-bottom: 15px;
            color: var(--primary-dark);
        }
        
        h4 {
            font-size: 18px;
            font-weight: 600;
            color: var(--accent-pink);
            margin-bottom: 10px;
        }
        
        p {
            margin-bottom: 15px;
        }
        
        .subtitle {
            font-size: 16px;
            font-weight: 400;
            color: var(--text-medium);
            line-height: 1.8;
        }
        
        /* LAYOUT */
        .report-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 60px 40px;
            background: var(--bg-white);
        }
        
        .report-section {
            margin-bottom: 60px;
            page-break-inside: avoid;
        }
        
        .grid-2col {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
        }
        
        .grid-3col {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 30px;
        }
        
        /* PDF-EXPORT-BUTTON */
        .report-header {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
        }
        
        .pdf-export-btn {
            background: var(--accent-pink);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(231, 76, 60, 0.3);
            transition: all 0.2s;
        }
        
        .pdf-export-btn:hover {
            background: #C0392B;
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(231, 76, 60, 0.4);
        }
        
        /* COVER PAGE */
        .report-cover {
            min-height: 100vh;
            background: linear-gradient(135deg, #2C3E50 0%, #34495E 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 60px;
            position: relative;
            page-break-after: always;
        }
        
        .cover-content {
            width: 100%;
            max-width: 800px;
        }
        
        .logo-container {
            position: absolute;
            top: 40px;
            right: 40px;
            text-align: center;
        }
        
        .logo-circle {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            background: var(--accent-pink);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 10px;
            font-size: 36px;
        }
        
        .logo-text {
            color: white;
            font-size: 11px;
            font-weight: 600;
            line-height: 1.3;
            text-align: center;
        }
        
        .title-block {
            position: relative;
            padding-left: 40px;
            color: white;
        }
        
        .accent-line {
            width: 4px;
            height: 120px;
            background: var(--accent-pink);
            position: absolute;
            left: 0;
            top: 0;
        }
        
        .cover-title {
            font-size: 48px;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 20px;
        }
        
        .highlight {
            background: var(--accent-pink);
            padding: 5px 15px;
            display: inline-block;
        }
        
        .template-badge {
            background: var(--accent-pink);
            color: white;
            padding: 8px 20px;
            display: inline-block;
            font-weight: 700;
            font-size: 14px;
            letter-spacing: 1px;
            margin: 20px 0 30px 0;
        }
        
        .project-info {
            margin: 30px 0;
        }
        
        .project-info h3 {
            color: white;
            font-size: 24px;
            margin-bottom: 15px;
        }
        
        .report-meta {
            font-size: 13px;
            color: var(--text-light);
            line-height: 1.6;
            margin-top: 30px;
        }
        
        /* METRICS CARDS */
        .metrics-grid {
            margin-top: 30px;
        }
        
        .metric-card {
            background: var(--bg-card);
            border-left: 4px solid var(--primary-blue);
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        
        .metric-card.highlight-card {
            border-left-color: var(--accent-pink);
            background: linear-gradient(135deg, #FFF5F5 0%, var(--bg-card) 100%);
        }
        
        .metric-card h4 {
            margin: 0 0 10px 0;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-medium);
        }
        
        .metric-value {
            font-size: 36px;
            font-weight: 800;
            color: var(--primary-dark);
            margin: 10px 0 5px 0;
            line-height: 1;
        }
        
        .metric-unit {
            font-size: 14px;
            color: var(--text-medium);
            margin: 0 0 10px 0;
        }
        
        .metric-note {
            font-size: 12px;
            color: var(--text-light);
            margin: 0;
        }
        
        /* SITE SECTION */
        .site-section {
            background: var(--bg-white);
            border: 1px solid var(--border-light);
            border-radius: 12px;
            padding: 40px;
            margin-bottom: 40px;
            page-break-inside: avoid;
        }
        
        .site-header {
            border-bottom: 2px solid var(--accent-pink);
            padding-bottom: 15px;
            margin-bottom: 30px;
        }
        
        .site-metadata {
            margin: 30px 0;
        }
        
        .metadata-group {
            background: var(--bg-light-gray);
            padding: 20px;
            border-radius: 8px;
        }
        
        .info-table {
            width: 100%;
            margin-top: 15px;
        }
        
        .info-table td {
            padding: 8px 0;
            font-size: 14px;
        }
        
        .info-table td:first-child {
            color: var(--text-medium);
            width: 40%;
        }
        
        .info-table td:last-child {
            font-weight: 600;
            color: var(--text-dark);
        }
        
        /* MATERIAL BALANCE FLOW */
        .material-balance {
            margin: 40px 0;
        }
        
        .balance-flow {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin: 30px 0;
            padding: 30px;
            background: var(--bg-light-gray);
            border-radius: 12px;
            flex-wrap: wrap;
        }
        
        .flow-step {
            flex: 1;
            min-width: 150px;
        }
        
        .flow-box {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        
        .flow-box.cut { border-top: 4px solid var(--color-cut); }
        .flow-box.fill { border-top: 4px solid var(--color-fill); }
        .flow-box.process { border-top: 4px solid var(--color-process); }
        .flow-box.balance.surplus { border-top: 4px solid var(--color-surplus); }
        .flow-box.balance.deficit { border-top: 4px solid var(--color-deficit); }
        
        .flow-box h4 {
            margin: 0 0 10px 0;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-dark);
        }
        
        .flow-value {
            font-size: 28px;
            font-weight: 800;
            margin: 10px 0;
            color: var(--primary-dark);
        }
        
        .flow-note {
            font-size: 11px;
            color: var(--text-medium);
            margin: 5px 0 0 0;
        }
        
        .flow-arrow {
            font-size: 32px;
            color: var(--text-light);
            font-weight: 300;
            padding: 0 10px;
        }
        
        /* PROFILE SECTION */
        .profiles-section {
            margin-top: 50px;
            page-break-before: always;
        }
        
        .profile-subsection {
            margin: 30px 0;
        }
        
        .profile-subsection h3 {
            color: var(--primary-dark);
            border-bottom: 2px solid var(--accent-pink);
            padding-bottom: 10px;
            margin-bottom: 25px;
        }
        
        .profile-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .profile-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.12);
        }
        
        .profile-card h4 {
            margin: 0 0 15px 0;
            color: var(--primary-dark);
            font-size: 16px;
            text-align: center;
        }
        
        .profile-image-container {
            background: white;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 15px;
            border: 1px solid var(--border-light);
        }
        
        .profile-image {
            width: 100%;
            height: auto;
            display: block;
            border-radius: 4px;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        
        .profile-image:hover {
            opacity: 0.9;
        }
        
        .download-btn {
            display: block;
            text-align: center;
            padding: 10px 15px;
            background: var(--accent-pink);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            transition: background 0.2s;
        }
        
        .download-btn:hover {
            background: #C0392B;
        }
        
        /* MODAL */
        .modal {
            display: none;
            position: fixed;
            z-index: 9999;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.95);
            overflow: auto;
        }
        
        .modal-content {
            margin: auto;
            display: block;
            max-width: 90%;
            max-height: 85vh;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            border-radius: 8px;
            box-shadow: 0 4px 30px rgba(0,0,0,0.5);
        }
        
        .modal-close {
            position: absolute;
            top: 20px;
            right: 40px;
            color: white;
            font-size: 50px;
            font-weight: bold;
            cursor: pointer;
            transition: color 0.2s;
            z-index: 10000;
        }
        
        .modal-close:hover {
            color: var(--accent-pink);
        }
        
        #modalCaption {
            text-align: center;
            color: white;
            padding: 20px;
            font-size: 18px;
            font-weight: 600;
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0,0,0,0.7);
            border-radius: 8px;
            padding: 15px 30px;
        }
        
        /* FOOTER */
        .report-footer {
            margin-top: 60px;
            padding-top: 30px;
            border-top: 2px solid var(--border-light);
            text-align: center;
            color: var(--text-medium);
            font-size: 12px;
        }
        
        /* PRINT STYLES */
        @media print {
            @page {
                size: A4;
                margin: 15mm;
            }
            
            .report-cover {
                page-break-after: always;
                min-height: 100vh;
            }
            
            .report-section,
            .site-section,
            .profile-card {
                page-break-inside: avoid;
            }
            
            .profiles-section {
                page-break-before: always;
            }
            
            a {
                text-decoration: none;
                color: inherit;
            }
            
            .download-btn,
            .pdf-export-btn,
            .report-header {
                display: none !important;
            }
            
            .modal {
                display: none !important;
            }
            
            img {
                max-width: 100%;
                page-break-inside: avoid;
            }
            
            .flow-arrow {
                font-size: 24px;
            }
        }
        
        /* RESPONSIVE */
        @media (max-width: 768px) {
            .grid-2col,
            .grid-3col {
                grid-template-columns: 1fr;
            }
            
            .balance-flow {
                flex-direction: column;
            }
            
            .flow-arrow {
                transform: rotate(90deg);
                margin: 15px 0;
            }
            
            .report-container {
                padding: 30px 20px;
            }
            
            h1 { font-size: 32px; }
            h2 { font-size: 24px; }
            h3 { font-size: 20px; }
        }
        """
    
    def _create_cover_page_html(self, project_name, total_sites, report_date, report_time):
        """Erstellt Cover-Page"""
        return f"""
    <div class="report-cover">
        <div class="cover-content">
            <div class="logo-container">
                <div class="logo-circle">🌬️</div>
                <p class="logo-text">Wind Turbine<br>Earthwork<br>Calculator</p>
            </div>
            
            <div class="title-block">
                <div class="accent-line"></div>
                <h1 class="cover-title">
                    ERDARBEITS-<br>
                    <span class="highlight">BERICHT</span>
                </h1>
                <div class="template-badge">STANDORT-ANALYSE</div>
                
                <div class="project-info">
                    <h3>{project_name}</h3>
                    <p class="subtitle">
                        Detaillierte Berechnung der Erdarbeitsvolumen für {total_sites} 
                        Windkraftanlagen-Standorte inkl. Fundamente, Kranstellflächen, 
                        Material-Bilanz und Geländeschnitte.
                    </p>
                </div>
                
                <p class="report-meta">
                    Erstellt am: {report_date}, {report_time} Uhr<br>
                    Tool-Version: {self.version} | Standorte: {total_sites}
                </p>
            </div>
        </div>
    </div>
        """
    
    def _create_summary_page_html(self, total_sites, total_cut, total_fill, total_balance):
        """Erstellt Zusammenfassungs-Seite"""
        balance_status = "Überschuss" if total_balance > 0 else "Mangel"
        
        return f"""
    <div class="report-container">
        <div class="report-section summary-section">
            <h2>Projekt-Übersicht</h2>
            <p class="subtitle">
                Dieser Bericht fasst die Erdarbeitsvolumen für {total_sites} 
                Windkraftanlagen-Standorte zusammen, inklusive detaillierter 
                Material-Bilanz, Kostenabschätzung und Geländeschnitten.
            </p>
            
            <div class="metrics-grid grid-3col">
                <div class="metric-card">
                    <h4>Gesamt-Aushub</h4>
                    <p class="metric-value">{total_cut:,.0f}</p>
                    <p class="metric-unit">m³</p>
                    <p class="metric-note">In-situ Volumen (gewachsen)</p>
                </div>
                
                <div class="metric-card">
                    <h4>Gesamt-Auftrag</h4>
                    <p class="metric-value">{total_fill:,.0f}</p>
                    <p class="metric-unit">m³</p>
                    <p class="metric-note">Verdichtet eingebaut</p>
                </div>
                
                <div class="metric-card highlight-card">
                    <h4>Material-Saldo</h4>
                    <p class="metric-value">{abs(total_balance):,.0f}</p>
                    <p class="metric-unit">m³</p>
                    <p class="metric-note">{balance_status}</p>
                </div>
            </div>
        </div>
    </div>
        """
    
    def _create_all_sites_html(self, results_list, profile_output_folder, html_output_path):
        """Erstellt HTML für alle Standorte"""
        sites_html = '<div class="report-container">'
        
        for i, result in enumerate(results_list, 1):
            site_id = i
            sites_html += self._create_site_detail_html(site_id, result)
            
            if profile_output_folder:
                profile_paths = self._get_profile_paths_for_site(
                    site_id, profile_output_folder, os.path.dirname(html_output_path)
                )
                if profile_paths:
                    sites_html += self._create_profile_section_html(site_id, profile_paths)
        
        sites_html += '</div>'
        return sites_html
    
    def _create_site_detail_html(self, site_id, result):
        """Erstellt HTML für Standort-Details (Feld-Namen aus prototype.py)"""
        total_cut = result.get('total_cut', 0)
        total_fill = result.get('total_fill', 0)
        balance = total_cut - total_fill
        balance_class = 'surplus' if balance > 0 else 'deficit'
        balance_text = 'Überschuss' if balance > 0 else 'Mangel'
        balance_action = 'Abtransport' if balance > 0 else 'Anlieferung'
        
        excavated = result.get('excavated_volume', total_cut * 1.25)
        platform_area = result.get('platform_area', 0)
        
        return f"""
    <div class="report-section site-section">
        <div class="site-header">
            <h2>Standort {site_id} - Detail-Analyse</h2>
        </div>
        
        <div class="site-metadata grid-2col">
            <div class="metadata-group">
                <h4>Fundament</h4>
                <table class="info-table">
                    <tr>
                        <td>Volumen:</td>
                        <td>{result.get('foundation_volume', 0):.1f} m³</td>
                    </tr>
                    <tr>
                        <td>Tiefe:</td>
                        <td>{result.get('foundation_depth_avg', 0):.2f} m</td>
                    </tr>
                    <tr>
                        <td>Fläche:</td>
                        <td>{platform_area:.1f} m²</td>
                    </tr>
                </table>
            </div>
            
            <div class="metadata-group">
                <h4>Kranstellfläche</h4>
                <table class="info-table">
                    <tr>
                        <td>Plattform Cut:</td>
                        <td>{result.get('platform_cut', 0):.1f} m³</td>
                    </tr>
                    <tr>
                        <td>Plattform Fill:</td>
                        <td>{result.get('platform_fill', 0):.1f} m³</td>
                    </tr>
                    <tr>
                        <td>Slope Cut:</td>
                        <td>{result.get('slope_cut', 0):.1f} m³</td>
                    </tr>
                    <tr>
                        <td>Slope Fill:</td>
                        <td>{result.get('slope_fill', 0):.1f} m³</td>
                    </tr>
                    <tr>
                        <td>Fläche:</td>
                        <td>{platform_area:.1f} m²</td>
                    </tr>
                </table>
            </div>
        </div>
        
        <div class="material-balance">
            <h3>Material-Bilanz</h3>
            <div class="balance-flow">
                <div class="flow-step">
                    <div class="flow-box cut">
                        <h4>Aushub</h4>
                        <p class="flow-value">{total_cut:.0f}</p>
                        <p class="flow-note">m³ (in-situ)</p>
                    </div>
                </div>
                
                <div class="flow-arrow">→</div>
                
                <div class="flow-step">
                    <div class="flow-box process">
                        <h4>Aufgelockert</h4>
                        <p class="flow-value">{excavated:.0f}</p>
                        <p class="flow-note">m³ (LKW-Volumen)</p>
                    </div>
                </div>
                
                <div class="flow-arrow">→</div>
                
                <div class="flow-step">
                    <div class="flow-box fill">
                        <h4>Auftrag</h4>
                        <p class="flow-value">{total_fill:.0f}</p>
                        <p class="flow-note">m³ (verdichtet)</p>
                    </div>
                </div>
                
                <div class="flow-arrow">→</div>
                
                <div class="flow-step">
                    <div class="flow-box balance {balance_class}">
                        <h4>{balance_text}</h4>
                        <p class="flow-value">{abs(balance):.0f}</p>
                        <p class="flow-note">m³ ({balance_action})</p>
                    </div>
                </div>
            </div>
        </div>
    </div>
        """
    
    def _get_profile_paths_for_site(self, site_id, profile_folder, html_folder):
        """Sucht PNG-Dateien für einen Standort"""
        profile_paths = []
        
        profile_types = [
            'Foundation_NS', 'Foundation_EW',
            'Crane_Longitudinal', 'Crane_Cross',
            'Crane_Edge_N', 'Crane_Edge_E', 'Crane_Edge_S', 'Crane_Edge_W'
        ]
        
        for ptype in profile_types:
            filename = f"Site_{site_id}_{ptype}.png"
            filepath = os.path.join(profile_folder, filename)
            
            if os.path.exists(filepath):
                rel_path = os.path.relpath(filepath, html_folder)
                profile_paths.append({
                    'type': ptype,
                    'path': rel_path.replace('\\', '/'),
                    'filename': filename
                })
        
        return profile_paths
    
    def _create_profile_section_html(self, site_id, profile_paths):
        """Erstellt HTML-Sektion für Geländeschnitte"""
        if not profile_paths:
            return ""
        
        foundation_profiles = [p for p in profile_paths if 'Foundation' in p['type']]
        crane_profiles = [p for p in profile_paths if 'Crane' in p['type']]
        
        return f"""
    <div class="report-section profiles-section">
        <h2>Geländeschnitte - Standort {site_id}</h2>
        <p class="subtitle">
            Visualisierung der Geländemodellierung für Fundament und Kranstellfläche 
            mit Cut/Fill-Bereichen. Klicken Sie auf ein Bild für Vollansicht.
        </p>
        
        {self._create_profile_grid_html('Fundament-Schnitte', foundation_profiles)}
        {self._create_profile_grid_html('Kranstellflächen-Schnitte', crane_profiles)}
    </div>
        """
    
    def _create_profile_grid_html(self, title, profile_list):
        """Erstellt Grid mit Profil-Thumbnails"""
        if not profile_list:
            return ""
        
        type_names = {
            'Foundation_NS': 'Fundament Nord-Süd',
            'Foundation_EW': 'Fundament Ost-West',
            'Crane_Longitudinal': 'Kranfläche Längsschnitt',
            'Crane_Cross': 'Kranfläche Querschnitt',
            'Crane_Edge_N': 'Kranfläche Nordkante',
            'Crane_Edge_E': 'Kranfläche Ostkante',
            'Crane_Edge_S': 'Kranfläche Südkante',
            'Crane_Edge_W': 'Kranfläche Westkante'
        }
        
        profiles_html = ""
        for profile in profile_list:
            ptype = profile['type']
            display_name = type_names.get(ptype, ptype)
            
            profiles_html += f"""
        <div class="profile-card">
            <h4>{display_name}</h4>
            <div class="profile-image-container">
                <img src="{profile['path']}" 
                     alt="{display_name}" 
                     class="profile-image"
                     onclick="openProfileModal(this)">
            </div>
            <a href="{profile['path']}" download="{profile['filename']}" class="download-btn">
                ⬇ PNG herunterladen
            </a>
        </div>
            """
        
        return f"""
    <div class="profile-subsection">
        <h3>{title}</h3>
        <div class="profile-grid grid-2col">
            {profiles_html}
        </div>
    </div>
        """
    
    def _create_footer_html(self, report_date, report_time):
        """Erstellt Footer"""
        return f"""
    <div class="report-container">
        <div class="report-footer">
            <p>
                <strong>Wind Turbine Earthwork Calculator v{self.version}</strong><br>
                Bericht erstellt am {report_date} um {report_time} Uhr<br>
                © 2025 | Alle Berechnungen basieren auf DGM-Daten und parametrisierten Annahmen
            </p>
        </div>
    </div>
        """
    
    def _create_modal_html(self):
        """Erstellt Modal für Vollbild-Ansicht"""
        return """
    <div id="profileModal" class="modal">
        <span class="modal-close" onclick="closeProfileModal()">&times;</span>
        <img class="modal-content" id="modalImage" alt="Profile">
        <div id="modalCaption"></div>
    </div>
        """
    
    def _get_report_javascript(self):
        """JavaScript für Modal-Funktionalität"""
        return """
        function openProfileModal(img) {
            var modal = document.getElementById('profileModal');
            var modalImg = document.getElementById('modalImage');
            var caption = document.getElementById('modalCaption');
            
            modal.style.display = 'block';
            modalImg.src = img.src;
            caption.innerHTML = img.alt;
            
            modal.style.opacity = '0';
            setTimeout(function() {
                modal.style.transition = 'opacity 0.3s';
                modal.style.opacity = '1';
            }, 10);
        }
        
        function closeProfileModal() {
            var modal = document.getElementById('profileModal');
            modal.style.opacity = '0';
            setTimeout(function() {
                modal.style.display = 'none';
            }, 300);
        }
        
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeProfileModal();
            }
        });
        
        document.getElementById('profileModal').addEventListener('click', function(event) {
            if (event.target.id === 'profileModal') {
                closeProfileModal();
            }
        });
        
        window.addEventListener('beforeprint', function() {
            console.log('Bereite PDF-Export vor...');
        });
        
        window.addEventListener('afterprint', function() {
            console.log('PDF-Export abgeschlossen.');
        });
        """
