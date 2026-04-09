"""
Site Aggregation for Multi-Site Comparison

Aggregates volumes and costs across multiple wind turbine sites for
comparison reports and project-level analysis.

Author: Wind Energy Site Planning
Version: 2.0.0 - Multi-Site Comparison Extension
"""

from typing import Dict, List, Optional, Any
from .site_data import SiteData, MultiSiteProject


class SiteAggregator:
    """
    Aggregates earthwork volumes and costs across multiple sites.

    This class provides methods to aggregate calculation results from multiple
    wind turbine sites for project-level reporting and comparison.
    """

    def __init__(self):
        """Initialize the SiteAggregator."""
        pass

    def aggregate_volumes(self, sites: List[SiteData]) -> Dict[str, float]:
        """
        Aggregate volume data across multiple sites.

        Args:
            sites: List of SiteData objects to aggregate

        Returns:
            Dictionary with aggregated volume metrics:
                - total_cut: Total cut volume (m³)
                - total_fill: Total fill volume (m³)
                - net_volume: Net volume = cut - fill (m³)
                - total_volume_moved: Total volume moved = cut + fill (m³)
                - avg_cut: Average cut per site (m³)
                - avg_fill: Average fill per site (m³)
                - avg_volume_moved: Average volume moved per site (m³)
                - min_volume_moved: Minimum volume moved at any site (m³)
                - max_volume_moved: Maximum volume moved at any site (m³)
                - site_count: Number of sites
        """
        if not sites:
            return {
                'total_cut': 0.0,
                'total_fill': 0.0,
                'net_volume': 0.0,
                'total_volume_moved': 0.0,
                'avg_cut': 0.0,
                'avg_fill': 0.0,
                'avg_volume_moved': 0.0,
                'min_volume_moved': 0.0,
                'max_volume_moved': 0.0,
                'site_count': 0
            }

        total_cut = sum(site.total_cut for site in sites)
        total_fill = sum(site.total_fill for site in sites)
        volumes_moved = [site.total_volume_moved for site in sites]
        site_count = len(sites)

        return {
            'total_cut': round(total_cut, 2),
            'total_fill': round(total_fill, 2),
            'net_volume': round(total_cut - total_fill, 2),
            'total_volume_moved': round(sum(volumes_moved), 2),
            'avg_cut': round(total_cut / site_count, 2),
            'avg_fill': round(total_fill / site_count, 2),
            'avg_volume_moved': round(sum(volumes_moved) / site_count, 2),
            'min_volume_moved': round(min(volumes_moved), 2),
            'max_volume_moved': round(max(volumes_moved), 2),
            'site_count': site_count
        }

    def aggregate_costs(self, sites: List[SiteData]) -> Dict[str, float]:
        """
        Aggregate cost data across multiple sites.

        Args:
            sites: List of SiteData objects to aggregate

        Returns:
            Dictionary with aggregated cost metrics:
                - total_cost: Total project cost (€)
                - cost_excavation: Total excavation costs (€)
                - cost_transport: Total transport costs (€)
                - cost_fill: Total fill material costs (€)
                - cost_gravel: Total gravel costs (€)
                - cost_compaction: Total compaction costs (€)
                - cost_saving: Total savings from material reuse (€)
                - avg_cost: Average cost per site (€)
                - min_cost: Minimum cost at any site (€)
                - max_cost: Maximum cost at any site (€)
                - site_count: Number of sites
        """
        if not sites:
            return {
                'total_cost': 0.0,
                'cost_excavation': 0.0,
                'cost_transport': 0.0,
                'cost_fill': 0.0,
                'cost_gravel': 0.0,
                'cost_compaction': 0.0,
                'cost_saving': 0.0,
                'avg_cost': 0.0,
                'min_cost': 0.0,
                'max_cost': 0.0,
                'site_count': 0
            }

        site_count = len(sites)
        site_costs = [site.total_cost for site in sites]

        # Sum up each cost category
        total_cost = sum(site.costs.get('cost_total', 0.0) for site in sites)
        cost_excavation = sum(site.costs.get('cost_excavation', 0.0) for site in sites)
        cost_transport = sum(site.costs.get('cost_transport', 0.0) for site in sites)
        cost_fill = sum(site.costs.get('cost_fill', 0.0) for site in sites)
        cost_gravel = sum(site.costs.get('cost_gravel', 0.0) for site in sites)
        cost_compaction = sum(site.costs.get('cost_compaction', 0.0) for site in sites)
        cost_saving = sum(site.costs.get('cost_saving', 0.0) for site in sites)

        return {
            'total_cost': round(total_cost, 2),
            'cost_excavation': round(cost_excavation, 2),
            'cost_transport': round(cost_transport, 2),
            'cost_fill': round(cost_fill, 2),
            'cost_gravel': round(cost_gravel, 2),
            'cost_compaction': round(cost_compaction, 2),
            'cost_saving': round(cost_saving, 2),
            'avg_cost': round(total_cost / site_count, 2),
            'min_cost': round(min(site_costs), 2),
            'max_cost': round(max(site_costs), 2),
            'site_count': site_count
        }

    def aggregate_project(self, project: MultiSiteProject) -> Dict[str, Any]:
        """
        Aggregate all data for a multi-site project.

        Args:
            project: MultiSiteProject with sites to aggregate

        Returns:
            Dictionary with complete project aggregation including:
                - project_name: Name of the project
                - volumes: Aggregated volume data
                - costs: Aggregated cost data
                - statistics: Project-level statistics
        """
        volumes = self.aggregate_volumes(project.sites)
        costs = self.aggregate_costs(project.sites)

        return {
            'project_name': project.project_name,
            'site_count': project.site_count,
            'volumes': volumes,
            'costs': costs,
            'statistics': project.get_statistics()
        }

    def get_cost_breakdown_by_site(self, sites: List[SiteData]) -> List[Dict[str, Any]]:
        """
        Get detailed cost breakdown for each site.

        Args:
            sites: List of SiteData objects

        Returns:
            List of dictionaries, one per site, with complete cost breakdown
        """
        breakdown = []

        for site in sites:
            breakdown.append({
                'site_id': site.site_id,
                'site_name': site.site_name,
                'total_cost': round(site.total_cost, 2),
                'cost_excavation': round(site.costs.get('cost_excavation', 0.0), 2),
                'cost_transport': round(site.costs.get('cost_transport', 0.0), 2),
                'cost_fill': round(site.costs.get('cost_fill', 0.0), 2),
                'cost_gravel': round(site.costs.get('cost_gravel', 0.0), 2),
                'cost_compaction': round(site.costs.get('cost_compaction', 0.0), 2),
                'cost_saving': round(site.costs.get('cost_saving', 0.0), 2),
                'total_volume_moved': round(site.total_volume_moved, 2),
                'total_cut': round(site.total_cut, 2),
                'total_fill': round(site.total_fill, 2),
                'complexity_score': round(site.get_complexity_score(), 2)
            })

        return breakdown

    def get_volume_breakdown_by_site(self, sites: List[SiteData]) -> List[Dict[str, Any]]:
        """
        Get detailed volume breakdown for each site.

        Args:
            sites: List of SiteData objects

        Returns:
            List of dictionaries, one per site, with complete volume breakdown
        """
        breakdown = []

        for site in sites:
            breakdown.append({
                'site_id': site.site_id,
                'site_name': site.site_name,
                'total_cut': round(site.total_cut, 2),
                'total_fill': round(site.total_fill, 2),
                'net_volume': round(site.net_volume, 2),
                'total_volume_moved': round(site.total_volume_moved, 2),
                'crane_height': round(site.crane_height, 2),
                'fok': round(site.fok, 2),
                'location_x': round(site.location.x(), 2),
                'location_y': round(site.location.y(), 2)
            })

        return breakdown

    def get_ranked_sites(
        self,
        sites: List[SiteData],
        sort_by: str = 'complexity'
    ) -> List[SiteData]:
        """
        Get sites ranked by various criteria.

        Args:
            sites: List of SiteData objects
            sort_by: Sorting criterion - 'complexity', 'cost', 'volume', or 'cut'

        Returns:
            Sorted list of SiteData (highest first)

        Raises:
            ValueError: If sort_by criterion is invalid
        """
        if sort_by == 'complexity':
            return sorted(sites, key=lambda s: s.get_complexity_score(), reverse=True)
        elif sort_by == 'cost':
            return sorted(sites, key=lambda s: s.total_cost, reverse=True)
        elif sort_by == 'volume':
            return sorted(sites, key=lambda s: s.total_volume_moved, reverse=True)
        elif sort_by == 'cut':
            return sorted(sites, key=lambda s: s.total_cut, reverse=True)
        else:
            raise ValueError(f"Invalid sort_by criterion: {sort_by}. "
                           f"Must be one of: 'complexity', 'cost', 'volume', 'cut'")

    def calculate_cost_distribution(self, sites: List[SiteData]) -> Dict[str, float]:
        """
        Calculate percentage distribution of costs across categories.

        Args:
            sites: List of SiteData objects

        Returns:
            Dictionary with percentage of total cost for each category:
                - pct_excavation: Percentage for excavation
                - pct_transport: Percentage for transport
                - pct_fill: Percentage for fill material
                - pct_gravel: Percentage for gravel
                - pct_compaction: Percentage for compaction
        """
        if not sites:
            return {
                'pct_excavation': 0.0,
                'pct_transport': 0.0,
                'pct_fill': 0.0,
                'pct_gravel': 0.0,
                'pct_compaction': 0.0
            }

        costs = self.aggregate_costs(sites)
        total = costs['total_cost']

        if total == 0:
            return {
                'pct_excavation': 0.0,
                'pct_transport': 0.0,
                'pct_fill': 0.0,
                'pct_gravel': 0.0,
                'pct_compaction': 0.0
            }

        return {
            'pct_excavation': round((costs['cost_excavation'] / total) * 100, 1),
            'pct_transport': round((costs['cost_transport'] / total) * 100, 1),
            'pct_fill': round((costs['cost_fill'] / total) * 100, 1),
            'pct_gravel': round((costs['cost_gravel'] / total) * 100, 1),
            'pct_compaction': round((costs['cost_compaction'] / total) * 100, 1)
        }
