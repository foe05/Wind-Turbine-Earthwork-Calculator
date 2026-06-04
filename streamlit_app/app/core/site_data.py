"""
Site-Data und MultiSiteProject (Port aus core/site_data.py + site_aggregator.py).

Datacontainer für einzelne WEA-Standorte + Aggregation über Multi-Site-Projekt
(Sortierung, Statistik, Ranking, Export-Helfer).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from shapely.geometry import Point

from .multi_surface import MultiSurfaceResult


@dataclass
class SiteData:
    """Eine WEA mit Berechnungsergebnis + Kosten."""

    site_id: str
    site_name: str
    location: Point  # turbine center
    result: MultiSurfaceResult
    costs: dict[str, float] = field(default_factory=dict)

    project_config: Optional[Any] = None
    calculation_timestamp: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.site_id:
            raise ValueError("site_id darf nicht leer sein")
        if not self.site_name:
            raise ValueError("site_name darf nicht leer sein")
        if self.calculation_timestamp is None:
            self.calculation_timestamp = datetime.now()

    @property
    def total_cut(self) -> float:
        return self.result.total_cut_m3

    @property
    def total_fill(self) -> float:
        return self.result.total_fill_m3

    @property
    def net_volume(self) -> float:
        return self.result.net_m3

    @property
    def total_volume_moved(self) -> float:
        return self.result.total_moved_m3

    @property
    def total_cost(self) -> float:
        return float(self.costs.get("cost_total", 0.0))

    @property
    def crane_height(self) -> float:
        return self.result.crane_optimum_height

    @property
    def fok(self) -> float:
        return self.result.fok


@dataclass
class MultiSiteProject:
    """Sammlung mehrerer Sites für Vergleich + Aggregation."""

    project_name: str
    sites: list[SiteData] = field(default_factory=list)
    project_metadata: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.project_name:
            raise ValueError("project_name darf nicht leer sein")
        if self.created_at is None:
            self.created_at = datetime.now()

    def add_site(self, site: SiteData) -> None:
        if any(s.site_id == site.site_id for s in self.sites):
            raise ValueError(f"Site '{site.site_id}' existiert bereits")
        self.sites.append(site)

    def remove_site(self, site_id: str) -> bool:
        before = len(self.sites)
        self.sites = [s for s in self.sites if s.site_id != site_id]
        return len(self.sites) < before

    @property
    def site_count(self) -> int:
        return len(self.sites)

    @property
    def total_cut(self) -> float:
        return sum(s.total_cut for s in self.sites)

    @property
    def total_fill(self) -> float:
        return sum(s.total_fill for s in self.sites)

    @property
    def total_net_volume(self) -> float:
        return self.total_cut - self.total_fill

    @property
    def total_cost(self) -> float:
        return sum(s.total_cost for s in self.sites)

    def rank_by(self, key: str, reverse: bool = False) -> list[SiteData]:
        """Sortiert Sites nach einem Attributnamen (z. B. 'total_cost', 'total_cut')."""
        return sorted(self.sites, key=lambda s: getattr(s, key, 0.0), reverse=reverse)

    def best_site(self, key: str = "total_cost") -> Optional[SiteData]:
        if not self.sites:
            return None
        return min(self.sites, key=lambda s: getattr(s, key, 0.0))

    def worst_site(self, key: str = "total_cost") -> Optional[SiteData]:
        if not self.sites:
            return None
        return max(self.sites, key=lambda s: getattr(s, key, 0.0))

    def summary(self) -> dict:
        """Aggregierte Kennzahlen für Reports."""
        if not self.sites:
            return {"site_count": 0}
        cuts = [s.total_cut for s in self.sites]
        fills = [s.total_fill for s in self.sites]
        costs = [s.total_cost for s in self.sites]
        return {
            "project_name": self.project_name,
            "site_count": len(self.sites),
            "total_cut_m3": round(sum(cuts), 1),
            "total_fill_m3": round(sum(fills), 1),
            "total_net_volume_m3": round(self.total_net_volume, 1),
            "total_cost_eur": round(sum(costs), 2),
            "avg_cut_per_site_m3": round(sum(cuts) / len(cuts), 1),
            "avg_fill_per_site_m3": round(sum(fills) / len(fills), 1),
            "avg_cost_per_site_eur": round(sum(costs) / len(costs), 2),
            "max_cost_site": self.worst_site("total_cost").site_id if self.sites else None,
            "min_cost_site": self.best_site("total_cost").site_id if self.sites else None,
        }
