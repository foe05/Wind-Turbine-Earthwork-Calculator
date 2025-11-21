"""
Visualization functions for uncertainty analysis results.

Generates histograms, tornado diagrams, and other visualizations
for Monte Carlo uncertainty propagation results.

Author: Wind Energy Site Planning
Version: 2.0 - Uncertainty Extension
"""

import os
from typing import Optional, Dict, List, Tuple
import numpy as np

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from .uncertainty import UncertaintyAnalysisResult, UncertaintyResult


def generate_uncertainty_visualizations(
    analysis_result: UncertaintyAnalysisResult,
    output_dir: str,
    prefix: str = "uncertainty"
) -> Dict[str, str]:
    """
    Generate all uncertainty visualizations and save to files.

    Args:
        analysis_result: Results from uncertainty analysis
        output_dir: Directory to save images
        prefix: Filename prefix for output files

    Returns:
        Dictionary mapping visualization names to file paths
    """
    if not MATPLOTLIB_AVAILABLE:
        return {}

    os.makedirs(output_dir, exist_ok=True)
    output_files = {}

    # 1. Histogram of optimal crane heights
    crane_height_path = os.path.join(output_dir, f"{prefix}_crane_height_histogram.png")
    generate_histogram(
        analysis_result.crane_height,
        title="Verteilung der optimalen Kranstellhöhe",
        xlabel="Höhe (m ü.NN)",
        ylabel="Häufigkeit",
        output_path=crane_height_path,
        color='steelblue'
    )
    output_files['crane_height_histogram'] = crane_height_path

    # 2. Histogram of total cut volume
    cut_path = os.path.join(output_dir, f"{prefix}_cut_volume_histogram.png")
    generate_histogram(
        analysis_result.total_cut,
        title="Verteilung des Abtragsvolumens",
        xlabel="Volumen (m³)",
        ylabel="Häufigkeit",
        output_path=cut_path,
        color='indianred'
    )
    output_files['cut_volume_histogram'] = cut_path

    # 3. Histogram of total fill volume
    fill_path = os.path.join(output_dir, f"{prefix}_fill_volume_histogram.png")
    generate_histogram(
        analysis_result.total_fill,
        title="Verteilung des Auftragsvolumens",
        xlabel="Volumen (m³)",
        ylabel="Häufigkeit",
        output_path=fill_path,
        color='forestgreen'
    )
    output_files['fill_volume_histogram'] = fill_path

    # 4. Histogram of net volume
    net_path = os.path.join(output_dir, f"{prefix}_net_volume_histogram.png")
    generate_histogram(
        analysis_result.net_volume,
        title="Verteilung des Netto-Volumens (Abtrag - Auftrag)",
        xlabel="Volumen (m³)",
        ylabel="Häufigkeit",
        output_path=net_path,
        color='darkorange'
    )
    output_files['net_volume_histogram'] = net_path

    # 5. Tornado diagram for sensitivity
    if analysis_result.sensitivity:
        tornado_path = os.path.join(output_dir, f"{prefix}_tornado_diagram.png")
        generate_tornado_diagram(
            analysis_result,
            title="Sensitivitätsanalyse - Einfluss auf Gesamtvolumen",
            output_path=tornado_path
        )
        output_files['tornado_diagram'] = tornado_path

    # 6. Combined summary plot
    summary_path = os.path.join(output_dir, f"{prefix}_summary.png")
    generate_summary_plot(analysis_result, summary_path)
    output_files['summary'] = summary_path

    return output_files


def generate_histogram(
    uncertainty_result: UncertaintyResult,
    title: str,
    xlabel: str,
    ylabel: str,
    output_path: str,
    color: str = 'steelblue',
    bins: int = 30
):
    """
    Generate histogram with statistics overlay.

    Args:
        uncertainty_result: Uncertainty result with samples
        title: Plot title
        xlabel: X-axis label
        ylabel: Y-axis label
        output_path: Path to save figure
        color: Histogram color
        bins: Number of histogram bins
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    samples = uncertainty_result.samples

    # Plot histogram
    n, bins_edges, patches = ax.hist(
        samples, bins=bins, color=color, alpha=0.7, edgecolor='black'
    )

    # Add vertical lines for statistics
    ax.axvline(
        uncertainty_result.mean, color='red', linestyle='-', linewidth=2,
        label=f'Mittelwert: {uncertainty_result.mean:.2f}'
    )
    ax.axvline(
        uncertainty_result.percentile_5, color='orange', linestyle='--', linewidth=1.5,
        label=f'5% Perzentil: {uncertainty_result.percentile_5:.2f}'
    )
    ax.axvline(
        uncertainty_result.percentile_95, color='orange', linestyle='--', linewidth=1.5,
        label=f'95% Perzentil: {uncertainty_result.percentile_95:.2f}'
    )

    # Add statistics text box
    stats_text = (
        f"Mittelwert: {uncertainty_result.mean:.2f}\n"
        f"Std.abw.: {uncertainty_result.std:.2f}\n"
        f"90% KI: [{uncertainty_result.percentile_5:.2f}, {uncertainty_result.percentile_95:.2f}]\n"
        f"CV: {uncertainty_result.coefficient_of_variation*100:.1f}%\n"
        f"N: {len(samples)}"
    )

    ax.text(
        0.98, 0.98, stats_text,
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment='top',
        horizontalalignment='right',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    )

    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def generate_tornado_diagram(
    analysis_result: UncertaintyAnalysisResult,
    title: str,
    output_path: str
):
    """
    Generate tornado diagram showing parameter sensitivities.

    Args:
        analysis_result: Complete uncertainty analysis result
        title: Plot title
        output_path: Path to save figure
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    # Get sensitivity ranking
    ranking = analysis_result.get_sensitivity_ranking()

    if not ranking:
        return

    # Prepare data
    param_names_display = {
        'fok': 'FOK (Fundamentoberkante)',
        'slope_angle': 'Böschungswinkel',
        'foundation_depth': 'Fundamenttiefe',
        'gravel_thickness': 'Kiesschichtstärke',
        'dem_noise': 'DGM-Messungenauigkeit',
        'boom_slope_noise': 'Auslegergefälle',
        'rotor_offset_noise': 'Rotorhöhenversatz',
    }

    labels = []
    values = []
    correlations = []

    for param_name, sensitivity in ranking:
        display_name = param_names_display.get(param_name, param_name)
        labels.append(display_name)
        values.append(sensitivity * 100)  # Convert to percentage

        if param_name in analysis_result.sensitivity:
            correlations.append(analysis_result.sensitivity[param_name].correlation)
        else:
            correlations.append(0)

    # Create figure
    fig, ax = plt.subplots(figsize=(12, max(6, len(labels) * 0.5)))

    y_pos = np.arange(len(labels))

    # Color based on correlation sign
    colors = ['indianred' if c < 0 else 'steelblue' for c in correlations]

    # Create horizontal bars
    bars = ax.barh(y_pos, values, align='center', color=colors, alpha=0.7, edgecolor='black')

    # Add value labels
    for i, (bar, val, corr) in enumerate(zip(bars, values, correlations)):
        width = bar.get_width()
        sign = '+' if corr >= 0 else '-'
        ax.text(
            width + 0.5, bar.get_y() + bar.get_height()/2,
            f'{val:.1f}% ({sign})',
            ha='left', va='center', fontsize=9
        )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels)
    ax.set_xlabel('Sensitivitätsindex (%)', fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold')

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='steelblue', alpha=0.7, label='Positive Korrelation'),
        Patch(facecolor='indianred', alpha=0.7, label='Negative Korrelation')
    ]
    ax.legend(handles=legend_elements, loc='lower right')

    ax.grid(True, axis='x', alpha=0.3)
    ax.set_xlim(0, max(values) * 1.2 if values else 100)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def generate_summary_plot(
    analysis_result: UncertaintyAnalysisResult,
    output_path: str
):
    """
    Generate a summary plot with key results.

    Args:
        analysis_result: Complete uncertainty analysis result
        output_path: Path to save figure
    """
    if not MATPLOTLIB_AVAILABLE:
        return

    fig = plt.figure(figsize=(14, 10))

    # Create grid of subplots
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

    # 1. Crane height histogram (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    samples = analysis_result.crane_height.samples
    ax1.hist(samples, bins=25, color='steelblue', alpha=0.7, edgecolor='black')
    ax1.axvline(analysis_result.crane_height.mean, color='red', linestyle='-', linewidth=2)
    ax1.axvline(analysis_result.crane_height.percentile_5, color='orange', linestyle='--')
    ax1.axvline(analysis_result.crane_height.percentile_95, color='orange', linestyle='--')
    ax1.set_xlabel('Höhe (m ü.NN)')
    ax1.set_ylabel('Häufigkeit')
    ax1.set_title('Optimale Kranstellhöhe', fontweight='bold')

    # 2. Total volume histogram (top right)
    ax2 = fig.add_subplot(gs[0, 1])
    samples = analysis_result.total_volume_moved.samples
    ax2.hist(samples, bins=25, color='purple', alpha=0.7, edgecolor='black')
    ax2.axvline(analysis_result.total_volume_moved.mean, color='red', linestyle='-', linewidth=2)
    ax2.axvline(analysis_result.total_volume_moved.percentile_5, color='orange', linestyle='--')
    ax2.axvline(analysis_result.total_volume_moved.percentile_95, color='orange', linestyle='--')
    ax2.set_xlabel('Volumen (m³)')
    ax2.set_ylabel('Häufigkeit')
    ax2.set_title('Gesamtvolumen bewegt', fontweight='bold')

    # 3. Cut vs Fill scatter (bottom left)
    ax3 = fig.add_subplot(gs[1, 0])
    cuts = analysis_result.total_cut.samples
    fills = analysis_result.total_fill.samples
    ax3.scatter(cuts, fills, alpha=0.3, s=10, color='darkgreen')
    ax3.plot([min(cuts), max(cuts)], [min(cuts), max(cuts)], 'r--', label='Ausgeglichen')
    ax3.set_xlabel('Abtrag (m³)')
    ax3.set_ylabel('Auftrag (m³)')
    ax3.set_title('Abtrag vs. Auftrag', fontweight='bold')
    ax3.legend()

    # 4. Summary statistics table (bottom right)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')

    # Create table data
    table_data = [
        ['Parameter', 'Mittelwert', 'Std.Abw.', '90% KI'],
        ['Kranstellhöhe (m)',
         f'{analysis_result.crane_height.mean:.2f}',
         f'{analysis_result.crane_height.std:.2f}',
         f'[{analysis_result.crane_height.percentile_5:.2f}, {analysis_result.crane_height.percentile_95:.2f}]'],
        ['Abtrag (m³)',
         f'{analysis_result.total_cut.mean:.0f}',
         f'{analysis_result.total_cut.std:.0f}',
         f'[{analysis_result.total_cut.percentile_5:.0f}, {analysis_result.total_cut.percentile_95:.0f}]'],
        ['Auftrag (m³)',
         f'{analysis_result.total_fill.mean:.0f}',
         f'{analysis_result.total_fill.std:.0f}',
         f'[{analysis_result.total_fill.percentile_5:.0f}, {analysis_result.total_fill.percentile_95:.0f}]'],
        ['Netto (m³)',
         f'{analysis_result.net_volume.mean:.0f}',
         f'{analysis_result.net_volume.std:.0f}',
         f'[{analysis_result.net_volume.percentile_5:.0f}, {analysis_result.net_volume.percentile_95:.0f}]'],
    ]

    table = ax4.table(
        cellText=table_data,
        loc='center',
        cellLoc='center',
        colWidths=[0.3, 0.2, 0.2, 0.3]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)

    # Style header row
    for i in range(4):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(color='white', fontweight='bold')

    ax4.set_title('Zusammenfassung der Ergebnisse', fontweight='bold', y=0.95)

    # Main title
    fig.suptitle(
        f'Unsicherheitsanalyse - {analysis_result.num_samples} Monte Carlo Samples',
        fontsize=14, fontweight='bold', y=1.02
    )

    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)


def generate_html_uncertainty_section(
    analysis_result: UncertaintyAnalysisResult,
    image_paths: Dict[str, str]
) -> str:
    """
    Generate HTML section for uncertainty analysis results.

    Args:
        analysis_result: Complete uncertainty analysis result
        image_paths: Dictionary mapping image names to file paths

    Returns:
        HTML string for inclusion in report
    """
    html = []

    # Section header
    html.append('<div class="uncertainty-section">')
    html.append('<h2>Unsicherheitsanalyse</h2>')
    html.append(f'<p>Monte Carlo Simulation mit {analysis_result.num_samples} Samples, '
                f'Berechnungszeit: {analysis_result.computation_time_seconds:.1f}s</p>')

    # Summary table
    html.append('<h3>Zusammenfassung der Ergebnisse</h3>')
    html.append('<table class="uncertainty-table">')
    html.append('<tr><th>Parameter</th><th>Mittelwert</th><th>Std.Abw.</th>'
                '<th>90% Konfidenzintervall</th><th>CV</th></tr>')

    # Crane height
    ch = analysis_result.crane_height
    html.append(f'<tr><td>Optimale Kranstellhöhe</td>'
                f'<td>{ch.mean:.2f} m</td>'
                f'<td>±{ch.std:.2f} m</td>'
                f'<td>[{ch.percentile_5:.2f}, {ch.percentile_95:.2f}] m</td>'
                f'<td>{ch.coefficient_of_variation*100:.1f}%</td></tr>')

    # Cut volume
    cut = analysis_result.total_cut
    html.append(f'<tr><td>Abtragsvolumen</td>'
                f'<td>{cut.mean:,.0f} m³</td>'
                f'<td>±{cut.std:,.0f} m³</td>'
                f'<td>[{cut.percentile_5:,.0f}, {cut.percentile_95:,.0f}] m³</td>'
                f'<td>{cut.coefficient_of_variation*100:.1f}%</td></tr>')

    # Fill volume
    fill = analysis_result.total_fill
    html.append(f'<tr><td>Auftragsvolumen</td>'
                f'<td>{fill.mean:,.0f} m³</td>'
                f'<td>±{fill.std:,.0f} m³</td>'
                f'<td>[{fill.percentile_5:,.0f}, {fill.percentile_95:,.0f}] m³</td>'
                f'<td>{fill.coefficient_of_variation*100:.1f}%</td></tr>')

    # Net volume
    net = analysis_result.net_volume
    html.append(f'<tr><td>Netto-Volumen</td>'
                f'<td>{net.mean:,.0f} m³</td>'
                f'<td>±{net.std:,.0f} m³</td>'
                f'<td>[{net.percentile_5:,.0f}, {net.percentile_95:,.0f}] m³</td>'
                f'<td>-</td></tr>')

    html.append('</table>')

    # Images
    if 'summary' in image_paths:
        html.append('<h3>Verteilungen</h3>')
        img_name = os.path.basename(image_paths['summary'])
        html.append(f'<img src="{img_name}" alt="Zusammenfassung" style="max-width:100%;">')

    if 'tornado_diagram' in image_paths:
        html.append('<h3>Sensitivitätsanalyse</h3>')
        img_name = os.path.basename(image_paths['tornado_diagram'])
        html.append(f'<img src="{img_name}" alt="Tornado-Diagramm" style="max-width:100%;">')

    # Sensitivity ranking
    if analysis_result.sensitivity:
        html.append('<h3>Parameterranking nach Einfluss</h3>')
        html.append('<table class="sensitivity-table">')
        html.append('<tr><th>Rang</th><th>Parameter</th><th>Sensitivität</th><th>Korrelation</th></tr>')

        param_names_display = {
            'fok': 'FOK (Fundamentoberkante)',
            'slope_angle': 'Böschungswinkel',
            'foundation_depth': 'Fundamenttiefe',
            'gravel_thickness': 'Kiesschichtstärke',
            'dem_noise': 'DGM-Messungenauigkeit',
        }

        ranking = analysis_result.get_sensitivity_ranking()
        for i, (param, sensitivity) in enumerate(ranking, 1):
            display_name = param_names_display.get(param, param)
            corr = analysis_result.sensitivity[param].correlation
            sign = '+' if corr >= 0 else ''
            html.append(f'<tr><td>{i}</td><td>{display_name}</td>'
                        f'<td>{sensitivity*100:.1f}%</td>'
                        f'<td>{sign}{corr:.3f}</td></tr>')

        html.append('</table>')

    # Configuration used
    html.append('<h3>Verwendete Unsicherheiten</h3>')
    html.append('<table class="config-table">')
    config = analysis_result.config
    html.append(f'<tr><td>DGM-Vertikalgenauigkeit (1σ)</td><td>{config.dem_vertical_std*100:.1f} cm</td></tr>')
    html.append(f'<tr><td>FOK-Unsicherheit (1σ)</td><td>{config.fok_std*100:.1f} cm</td></tr>')
    html.append(f'<tr><td>Fundamenttiefe-Unsicherheit (1σ)</td><td>{config.foundation_depth_std*100:.1f} cm</td></tr>')
    html.append(f'<tr><td>Kiesschicht-Unsicherheit (1σ)</td><td>{config.gravel_thickness_std*100:.1f} cm</td></tr>')
    html.append(f'<tr><td>Böschungswinkel-Unsicherheit (1σ)</td><td>{config.slope_angle_std:.1f}°</td></tr>')
    html.append(f'<tr><td>Geländetyp</td><td>{config.terrain_type.value}</td></tr>')
    html.append(f'<tr><td>Sampling-Methode</td><td>{"Latin Hypercube" if config.use_latin_hypercube else "Random"}</td></tr>')
    html.append('</table>')

    html.append('</div>')

    return '\n'.join(html)
