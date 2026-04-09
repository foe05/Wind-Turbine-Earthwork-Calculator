"""
Site Data Structures for Multi-Site Comparison

Defines data structures for storing and aggregating wind turbine site data
across multiple sites for comparison reports.

Author: Wind Energy Site Planning
Version: 2.0.0 - Multi-Site Comparison Extension
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from qgis.core import QgsPointXY, QgsGeometry

from .surface_types import MultiSurfaceCalculationResult


@dataclass
class SiteData:
    """
    Complete data for a single wind turbine site.

    This stores all calculation results, costs, and metadata for one site
    to enable multi-site comparison and aggregation.

    Attributes:
        site_id: Unique identifier for the site
        site_name: Human-readable site name (e.g., "WEA 01", "Turbine A")
        location: Geographic location (turbine center point)
        calculation_result: Complete earthwork calculation results
        costs: Dictionary of cost breakdown (from calculate_costs)
        project_config: Original MultiSurfaceProject configuration
        calculation_timestamp: When the calculation was performed
        metadata: Additional site metadata (DXF paths, notes, etc.)
    """
    site_id: str
    site_name: str
    location: QgsPointXY
    calculation_result: MultiSurfaceCalculationResult
    costs: Dict[str, float]

    # Optional fields
    project_config: Optional[Any] = None  # MultiSurfaceProject (avoid circular import)
    calculation_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate site data after initialization."""
        if not self.site_id:
            raise ValueError("site_id cannot be empty")
        if not self.site_name:
            raise ValueError("site_name cannot be empty")
        if self.calculation_result is None:
            raise ValueError("calculation_result is required")
        if not self.costs:
            raise ValueError("costs dictionary is required")

    @property
    def total_cut(self) -> float:
        """Total cut volume for this site (m³)."""
        return self.calculation_result.total_cut

    @property
    def total_fill(self) -> float:
        """Total fill volume for this site (m³)."""
        return self.calculation_result.total_fill

    @property
    def net_volume(self) -> float:
        """Net earthwork volume (cut - fill) for this site (m³)."""
        return self.calculation_result.net_volume

    @property
    def total_volume_moved(self) -> float:
        """Total volume moved (cut + fill) for this site (m³)."""
        return self.calculation_result.total_volume_moved

    @property
    def total_cost(self) -> float:
        """Total cost for this site (€)."""
        return self.costs.get('cost_total', 0.0)

    @property
    def crane_height(self) -> float:
        """Optimized crane pad height (m ü.NN)."""
        return self.calculation_result.crane_height

    @property
    def fok(self) -> float:
        """Foundation top edge elevation (m ü.NN)."""
        return self.calculation_result.fok

    @property
    def gravel_volume(self) -> float:
        """External gravel volume for this site (m³)."""
        return self.calculation_result.gravel_fill_external

    @property
    def terrain_min(self) -> float:
        """Minimum terrain elevation across all surfaces (m ü.NN)."""
        surface_results = self.calculation_result.surface_results.values()
        return min((r.terrain_min for r in surface_results), default=0.0)

    @property
    def terrain_max(self) -> float:
        """Maximum terrain elevation across all surfaces (m ü.NN)."""
        surface_results = self.calculation_result.surface_results.values()
        return max((r.terrain_max for r in surface_results), default=0.0)

    @property
    def terrain_mean(self) -> float:
        """Area-weighted mean terrain elevation across all surfaces (m ü.NN)."""
        surface_results = list(self.calculation_result.surface_results.values())
        if not surface_results:
            return 0.0
        total_area = sum(r.total_area for r in surface_results)
        if total_area == 0:
            return 0.0
        return sum(r.terrain_mean * r.total_area for r in surface_results) / total_area

    @property
    def platform_area(self) -> float:
        """Total platform area for this site (m²)."""
        return self.calculation_result.total_platform_area

    @property
    def total_area(self) -> float:
        """Total area (platform + slopes) for this site (m²)."""
        return self.calculation_result.total_platform_area + self.calculation_result.total_slope_area

    def get_complexity_score(self) -> float:
        """
        Calculate a complexity score for this site.

        Higher score = more complex site requiring more attention.
        Based on total volume moved and cost.

        Returns:
            Complexity score (arbitrary units for ranking)
        """
        # Weight total volume moved and cost equally
        volume_score = self.total_volume_moved / 100.0  # Normalize to ~similar scale
        cost_score = self.total_cost / 10000.0  # Normalize to ~similar scale
        return volume_score + cost_score


@dataclass
class MultiSiteProject:
    """
    Collection of multiple wind turbine sites for comparison.

    This aggregates data from multiple sites and provides methods for
    analysis, ranking, and report generation.

    Attributes:
        project_name: Name of the wind farm/project
        sites: List of SiteData for each turbine site
        project_metadata: Project-level metadata (location, client, etc.)
        created_at: When this multi-site project was created
    """
    project_name: str
    sites: List[SiteData] = field(default_factory=list)
    project_metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate multi-site project after initialization."""
        if not self.project_name:
            raise ValueError("project_name cannot be empty")
        if self.created_at is None:
            self.created_at = datetime.now()

    def add_site(self, site_data: SiteData):
        """
        Add a site to the project.

        Args:
            site_data: SiteData to add

        Raises:
            ValueError: If site_id already exists
        """
        if any(s.site_id == site_data.site_id for s in self.sites):
            raise ValueError(f"Site with id '{site_data.site_id}' already exists")
        self.sites.append(site_data)

    def remove_site(self, site_id: str) -> bool:
        """
        Remove a site from the project.

        Args:
            site_id: ID of site to remove

        Returns:
            True if site was removed, False if not found
        """
        original_len = len(self.sites)
        self.sites = [s for s in self.sites if s.site_id != site_id]
        return len(self.sites) < original_len

    def get_site(self, site_id: str) -> Optional[SiteData]:
        """
        Get a site by ID.

        Args:
            site_id: Site identifier

        Returns:
            SiteData or None if not found
        """
        for site in self.sites:
            if site.site_id == site_id:
                return site
        return None

    @property
    def site_count(self) -> int:
        """Number of sites in this project."""
        return len(self.sites)

    @property
    def total_cut(self) -> float:
        """Total cut volume across all sites (m³)."""
        return sum(site.total_cut for site in self.sites)

    @property
    def total_fill(self) -> float:
        """Total fill volume across all sites (m³)."""
        return sum(site.total_fill for site in self.sites)

    @property
    def net_volume(self) -> float:
        """Net earthwork volume across all sites (m³)."""
        return sum(site.net_volume for site in self.sites)

    @property
    def total_volume_moved(self) -> float:
        """Total volume moved across all sites (m³)."""
        return sum(site.total_volume_moved for site in self.sites)

    @property
    def total_cost(self) -> float:
        """Total cost across all sites (€)."""
        return sum(site.total_cost for site in self.sites)

    @property
    def average_cut(self) -> float:
        """Average cut volume per site (m³)."""
        return self.total_cut / self.site_count if self.site_count > 0 else 0.0

    @property
    def average_fill(self) -> float:
        """Average fill volume per site (m³)."""
        return self.total_fill / self.site_count if self.site_count > 0 else 0.0

    @property
    def average_cost(self) -> float:
        """Average cost per site (€)."""
        return self.total_cost / self.site_count if self.site_count > 0 else 0.0

    def get_sites_ranked_by_complexity(self) -> List[SiteData]:
        """
        Get sites ranked by complexity score (descending).

        Returns:
            List of SiteData sorted by complexity (most complex first)
        """
        return sorted(self.sites, key=lambda s: s.get_complexity_score(), reverse=True)

    def get_sites_ranked_by_cost(self) -> List[SiteData]:
        """
        Get sites ranked by total cost (descending).

        Returns:
            List of SiteData sorted by cost (highest first)
        """
        return sorted(self.sites, key=lambda s: s.total_cost, reverse=True)

    def get_sites_ranked_by_volume(self) -> List[SiteData]:
        """
        Get sites ranked by total volume moved (descending).

        Returns:
            List of SiteData sorted by volume (highest first)
        """
        return sorted(self.sites, key=lambda s: s.total_volume_moved, reverse=True)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get project statistics for reporting.

        Returns:
            Dictionary with min, max, avg, and total statistics
        """
        if not self.sites:
            return {
                'site_count': 0,
                'total_cut': 0.0,
                'total_fill': 0.0,
                'net_volume': 0.0,
                'total_volume_moved': 0.0,
                'total_cost': 0.0,
                'avg_cut': 0.0,
                'avg_fill': 0.0,
                'avg_volume_moved': 0.0,
                'avg_cost': 0.0,
                'min_volume_moved': 0.0,
                'max_volume_moved': 0.0,
                'min_cost': 0.0,
                'max_cost': 0.0,
            }

        volumes = [s.total_volume_moved for s in self.sites]
        costs = [s.total_cost for s in self.sites]

        return {
            'site_count': self.site_count,
            'total_cut': self.total_cut,
            'total_fill': self.total_fill,
            'net_volume': self.net_volume,
            'total_volume_moved': self.total_volume_moved,
            'total_cost': self.total_cost,
            'avg_cut': self.average_cut,
            'avg_fill': self.average_fill,
            'avg_volume_moved': sum(volumes) / len(volumes),
            'avg_cost': self.average_cost,
            'min_volume_moved': min(volumes),
            'max_volume_moved': max(volumes),
            'min_cost': min(costs),
            'max_cost': max(costs),
        }
