"""
Chart generation functions for PDF reports.

Generates bar charts and pie charts for cut/fill volume visualizations
to be embedded in PDF reports.

Author: Wind Energy Site Planning
Version: 2.0 - Enhanced PDF Report Generation
"""

import io
import base64
from typing import Optional, Dict, List, Tuple

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


def generate_volume_chart(
    cut_volume: float,
    fill_volume: float,
    output_format: str = "base64",
    title: str = "Erdarbeiten",
    figsize: Tuple[int, int] = (10, 6),
    dpi: int = 150
) -> Optional[str]:
    """
    Generate a bar chart comparing cut and fill volumes.

    Args:
        cut_volume: Cut volume in cubic meters
        fill_volume: Fill volume in cubic meters
        output_format: Output format - "base64" or "file"
        title: Chart title
        figsize: Figure size (width, height) in inches
        dpi: Resolution in dots per inch

    Returns:
        Base64 encoded PNG image string or None if matplotlib unavailable
    """
    if not MATPLOTLIB_AVAILABLE:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    categories = ['Abtrag', 'Auftrag']
    volumes = [cut_volume, fill_volume]
    colors = ['indianred', 'forestgreen']

    bars = ax.bar(categories, volumes, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)

    # Add value labels on bars
    for bar, volume in zip(bars, volumes):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.,
            height,
            f'{volume:,.0f} m³',
            ha='center',
            va='bottom',
            fontsize=11,
            fontweight='bold'
        )

    ax.set_ylabel('Volumen (m³)', fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')

    # Format y-axis with thousands separator
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

    plt.tight_layout()

    # Convert to base64
    if output_format == "base64":
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return image_base64
    else:
        plt.close(fig)
        return None


def generate_volume_pie_chart(
    cut_volume: float,
    fill_volume: float,
    output_format: str = "base64",
    title: str = "Volumenverteilung",
    figsize: Tuple[int, int] = (8, 8),
    dpi: int = 150
) -> Optional[str]:
    """
    Generate a pie chart showing cut/fill volume distribution.

    Args:
        cut_volume: Cut volume in cubic meters
        fill_volume: Fill volume in cubic meters
        output_format: Output format - "base64" or "file"
        title: Chart title
        figsize: Figure size (width, height) in inches
        dpi: Resolution in dots per inch

    Returns:
        Base64 encoded PNG image string or None if matplotlib unavailable
    """
    if not MATPLOTLIB_AVAILABLE:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    sizes = [cut_volume, fill_volume]
    labels = ['Abtrag', 'Auftrag']
    colors = ['indianred', 'forestgreen']
    explode = (0.05, 0.05)  # Slightly separate slices

    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        colors=colors,
        autopct=lambda pct: f'{pct:.1f}%\n({pct*sum(sizes)/100:,.0f} m³)',
        startangle=90,
        explode=explode,
        shadow=True,
        textprops={'fontsize': 11}
    )

    # Make percentage text bold
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    ax.set_title(title, fontsize=13, fontweight='bold')

    plt.tight_layout()

    # Convert to base64
    if output_format == "base64":
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return image_base64
    else:
        plt.close(fig)
        return None


def generate_volume_breakdown_chart(
    platform_cut: float,
    platform_fill: float,
    slope_cut: float,
    slope_fill: float,
    foundation_volume: float,
    output_format: str = "base64",
    title: str = "Volumenaufschlüsselung",
    figsize: Tuple[int, int] = (12, 6),
    dpi: int = 150
) -> Optional[str]:
    """
    Generate a stacked bar chart showing detailed volume breakdown.

    Args:
        platform_cut: Platform cut volume in cubic meters
        platform_fill: Platform fill volume in cubic meters
        slope_cut: Slope cut volume in cubic meters
        slope_fill: Slope fill volume in cubic meters
        foundation_volume: Foundation volume in cubic meters
        output_format: Output format - "base64" or "file"
        title: Chart title
        figsize: Figure size (width, height) in inches
        dpi: Resolution in dots per inch

    Returns:
        Base64 encoded PNG image string or None if matplotlib unavailable
    """
    if not MATPLOTLIB_AVAILABLE:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    categories = ['Abtrag', 'Auftrag', 'Fundament']

    # Stacked components
    platform_volumes = [platform_cut, platform_fill, 0]
    slope_volumes = [slope_cut, slope_fill, 0]
    foundation_volumes = [0, 0, foundation_volume]

    x = np.arange(len(categories))
    width = 0.6

    # Create stacked bars
    p1 = ax.bar(x, platform_volumes, width, label='Plattform', color='steelblue', edgecolor='black')
    p2 = ax.bar(x, slope_volumes, width, bottom=platform_volumes, label='Böschung', color='orange', edgecolor='black')
    p3 = ax.bar(x, foundation_volumes, width, label='Fundament', color='gray', edgecolor='black')

    # Add value labels
    for i, (pv, sv, fv) in enumerate(zip(platform_volumes, slope_volumes, foundation_volumes)):
        total = pv + sv + fv
        if total > 0:
            ax.text(
                i,
                total,
                f'{total:,.0f} m³',
                ha='center',
                va='bottom',
                fontsize=11,
                fontweight='bold'
            )

    ax.set_ylabel('Volumen (m³)', fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    # Format y-axis with thousands separator
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

    plt.tight_layout()

    # Convert to base64
    if output_format == "base64":
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return image_base64
    else:
        plt.close(fig)
        return None


def generate_multi_site_comparison_chart(
    sites_data: List[Dict],
    output_format: str = "base64",
    title: str = "Standortvergleich - Erdarbeiten",
    figsize: Tuple[int, int] = (14, 7),
    dpi: int = 150
) -> Optional[str]:
    """
    Generate a grouped bar chart comparing volumes across multiple sites.

    Args:
        sites_data: List of dictionaries with keys 'id', 'total_cut', 'total_fill'
        output_format: Output format - "base64" or "file"
        title: Chart title
        figsize: Figure size (width, height) in inches
        dpi: Resolution in dots per inch

    Returns:
        Base64 encoded PNG image string or None if matplotlib unavailable
    """
    if not MATPLOTLIB_AVAILABLE or not sites_data:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    site_ids = [site['id'] for site in sites_data]
    cut_volumes = [site['total_cut'] for site in sites_data]
    fill_volumes = [site['total_fill'] for site in sites_data]

    x = np.arange(len(site_ids))
    width = 0.35

    bars1 = ax.bar(x - width/2, cut_volumes, width, label='Abtrag', color='indianred', alpha=0.8, edgecolor='black')
    bars2 = ax.bar(x + width/2, fill_volumes, width, label='Auftrag', color='forestgreen', alpha=0.8, edgecolor='black')

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height,
                    f'{height:,.0f}',
                    ha='center',
                    va='bottom',
                    fontsize=9
                )

    ax.set_xlabel('Standort ID', fontsize=11)
    ax.set_ylabel('Volumen (m³)', fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'WKA {site_id}' for site_id in site_ids])
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    # Format y-axis with thousands separator
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

    plt.tight_layout()

    # Convert to base64
    if output_format == "base64":
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return image_base64
    else:
        plt.close(fig)
        return None


def generate_cost_comparison_chart(
    sites_data: List[Dict],
    output_format: str = "base64",
    title: str = "Standortvergleich - Kosten",
    figsize: Tuple[int, int] = (12, 6),
    dpi: int = 150
) -> Optional[str]:
    """
    Generate a bar chart comparing costs across multiple sites.

    Args:
        sites_data: List of dictionaries with keys 'id', 'cost_total'
        output_format: Output format - "base64" or "file"
        title: Chart title
        figsize: Figure size (width, height) in inches
        dpi: Resolution in dots per inch

    Returns:
        Base64 encoded PNG image string or None if matplotlib unavailable
    """
    if not MATPLOTLIB_AVAILABLE or not sites_data:
        return None

    fig, ax = plt.subplots(figsize=figsize)

    site_ids = [site['id'] for site in sites_data]
    costs = [site['cost_total'] for site in sites_data]

    bars = ax.bar(
        range(len(site_ids)),
        costs,
        color='steelblue',
        alpha=0.8,
        edgecolor='black',
        linewidth=1.5
    )

    # Add value labels on bars
    for bar, cost in zip(bars, costs):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.,
            height,
            f'€{cost:,.0f}',
            ha='center',
            va='bottom',
            fontsize=10,
            fontweight='bold'
        )

    ax.set_xlabel('Standort ID', fontsize=11)
    ax.set_ylabel('Gesamtkosten (€)', fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_xticks(range(len(site_ids)))
    ax.set_xticklabels([f'WKA {site_id}' for site_id in site_ids])
    ax.grid(True, alpha=0.3, axis='y')

    # Format y-axis with thousands separator
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'€{int(x):,}'))

    plt.tight_layout()

    # Convert to base64
    if output_format == "base64":
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=dpi, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close(fig)
        return image_base64
    else:
        plt.close(fig)
        return None


def is_matplotlib_available() -> bool:
    """
    Check if matplotlib is available.

    Returns:
        True if matplotlib can be imported, False otherwise
    """
    return MATPLOTLIB_AVAILABLE
