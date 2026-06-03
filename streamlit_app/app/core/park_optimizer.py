"""Park-wide Earthwork Optimizer (Port aus core/park_optimizer.py).

LP für Transport-only + MILP für joint candidate-selection + Transport.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence


@dataclass(frozen=True)
class SiteEarthwork:
    site_id: str
    x: float
    y: float
    cut_excess_m3: float = 0.0
    fill_need_m3: float = 0.0

    def __post_init__(self) -> None:
        if self.cut_excess_m3 < 0 or self.fill_need_m3 < 0:
            raise ValueError(
                f"cut_excess und fill_need >= 0 nötig; "
                f"bekam cut={self.cut_excess_m3}, fill={self.fill_need_m3}"
            )


@dataclass(frozen=True)
class SiteCandidate:
    cut_excess_m3: float
    fill_need_m3: float
    site_cost_eur: float = 0.0
    label: str = ""

    def __post_init__(self) -> None:
        if self.cut_excess_m3 < 0 or self.fill_need_m3 < 0:
            raise ValueError("cut_excess und fill_need müssen ≥ 0 sein")


@dataclass(frozen=True)
class SiteWithCandidates:
    site_id: str
    x: float
    y: float
    candidates: Sequence[SiteCandidate]

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ValueError(f"site {self.site_id} hat keine Kandidaten")


@dataclass(frozen=True)
class TransportConfig:
    cost_per_m3_km: float
    dump_cost_per_m3: float
    external_gravel_cost_per_m3: float
    max_distance_km: Optional[float] = None


@dataclass(frozen=True)
class TransportFlow:
    from_site: str
    to_site: str
    volume_m3: float
    distance_km: float
    transport_cost_eur: float


@dataclass
class ParkSolution:
    flows: list[TransportFlow] = field(default_factory=list)
    residual_dump_m3: dict[str, float] = field(default_factory=dict)
    residual_gravel_m3: dict[str, float] = field(default_factory=dict)
    total_transport_eur: float = 0.0
    total_dump_eur: float = 0.0
    total_gravel_eur: float = 0.0
    baseline_cost_eur: float = 0.0
    savings_eur: float = 0.0
    solver_status: str = ""

    @property
    def total_cost_eur(self) -> float:
        return self.total_transport_eur + self.total_dump_eur + self.total_gravel_eur


@dataclass
class ParkMILPSolution:
    chosen_index: dict[str, int] = field(default_factory=dict)
    chosen_candidate: dict[str, SiteCandidate] = field(default_factory=dict)
    flows: list[TransportFlow] = field(default_factory=list)
    residual_dump_m3: dict[str, float] = field(default_factory=dict)
    residual_gravel_m3: dict[str, float] = field(default_factory=dict)
    total_site_cost_eur: float = 0.0
    total_transport_eur: float = 0.0
    total_dump_eur: float = 0.0
    total_gravel_eur: float = 0.0
    solver_status: str = ""

    @property
    def total_cost_eur(self) -> float:
        return (
            self.total_site_cost_eur
            + self.total_transport_eur
            + self.total_dump_eur
            + self.total_gravel_eur
        )


def euclidean_distance_km(a, b) -> float:
    return math.hypot(a.x - b.x, a.y - b.y) / 1000.0


class ParkOptimizer:
    """LP- und MILP-Optimierer für Park-Material-Transport."""

    def __init__(
        self,
        config: TransportConfig,
        distance_fn: Callable = euclidean_distance_km,
    ):
        self.config = config
        self.distance_fn = distance_fn

    def solve(self, sites: Sequence[SiteEarthwork]) -> ParkSolution:
        if not sites:
            return ParkSolution(solver_status="empty input")
        from scipy.optimize import linprog

        n = len(sites)
        num_vars = n * n
        distances = [[0.0] * n for _ in range(n)]
        allowed = [[True] * n for _ in range(n)]
        for i, src in enumerate(sites):
            for j, dst in enumerate(sites):
                if i == j:
                    allowed[i][j] = False
                    continue
                d = self.distance_fn(src, dst)
                distances[i][j] = d
                if self.config.max_distance_km is not None and d > self.config.max_distance_km:
                    allowed[i][j] = False

        c_coeff = [0.0] * num_vars
        saved = self.config.dump_cost_per_m3 + self.config.external_gravel_cost_per_m3
        for i in range(n):
            for j in range(n):
                if not allowed[i][j]:
                    continue
                c_coeff[i * n + j] = self.config.cost_per_m3_km * distances[i][j] - saved

        bounds: list[tuple[float, Optional[float]]] = []
        for i in range(n):
            for j in range(n):
                bounds.append((0.0, None) if allowed[i][j] else (0.0, 0.0))

        a_ub: list[list[float]] = []
        b_ub: list[float] = []
        for i, src in enumerate(sites):
            row = [0.0] * num_vars
            for j in range(n):
                row[i * n + j] = 1.0
            a_ub.append(row)
            b_ub.append(src.cut_excess_m3)
        for j, dst in enumerate(sites):
            row = [0.0] * num_vars
            for i in range(n):
                row[i * n + j] = 1.0
            a_ub.append(row)
            b_ub.append(dst.fill_need_m3)

        result = linprog(c=c_coeff, A_ub=a_ub, b_ub=b_ub, bounds=bounds, method="highs")
        sol = ParkSolution(solver_status=result.message or ("ok" if result.success else "failed"))
        if not result.success:
            return sol

        consumed_out = [0.0] * n
        consumed_in = [0.0] * n
        for i in range(n):
            for j in range(n):
                vol = float(result.x[i * n + j])
                if vol <= 1e-6:
                    continue
                consumed_out[i] += vol
                consumed_in[j] += vol
                t_cost = self.config.cost_per_m3_km * distances[i][j] * vol
                sol.flows.append(
                    TransportFlow(
                        sites[i].site_id, sites[j].site_id, vol, distances[i][j], t_cost
                    )
                )
        sol.total_transport_eur = sum(f.transport_cost_eur for f in sol.flows)
        for i, s in enumerate(sites):
            residual = max(0.0, s.cut_excess_m3 - consumed_out[i])
            sol.residual_dump_m3[s.site_id] = residual
            sol.total_dump_eur += residual * self.config.dump_cost_per_m3
        for j, s in enumerate(sites):
            residual = max(0.0, s.fill_need_m3 - consumed_in[j])
            sol.residual_gravel_m3[s.site_id] = residual
            sol.total_gravel_eur += residual * self.config.external_gravel_cost_per_m3

        baseline = sum(
            s.cut_excess_m3 * self.config.dump_cost_per_m3
            + s.fill_need_m3 * self.config.external_gravel_cost_per_m3
            for s in sites
        )
        sol.baseline_cost_eur = baseline
        sol.savings_eur = baseline - sol.total_cost_eur
        return sol

    def solve_milp(self, sites: Sequence[SiteWithCandidates]) -> ParkMILPSolution:
        if not sites:
            return ParkMILPSolution(solver_status="empty input")
        import numpy as np
        from scipy.optimize import Bounds, LinearConstraint, milp

        n = len(sites)
        cand_counts = [len(s.candidates) for s in sites]
        num_y = sum(cand_counts)
        y_offset = [0] * n
        acc = 0
        for s in range(n):
            y_offset[s] = acc
            acc += cand_counts[s]

        def y_idx(s, k):
            return y_offset[s] + k

        def t_idx(i, j):
            return num_y + i * n + j

        num_t = n * n
        num_vars = num_y + num_t
        dump = self.config.dump_cost_per_m3
        gravel = self.config.external_gravel_cost_per_m3

        distances = [[0.0] * n for _ in range(n)]
        allowed = [[True] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    allowed[i][j] = False
                    continue
                d = self.distance_fn(sites[i], sites[j])
                distances[i][j] = d
                if self.config.max_distance_km is not None and d > self.config.max_distance_km:
                    allowed[i][j] = False

        c = np.zeros(num_vars)
        for s in range(n):
            for k, cand in enumerate(sites[s].candidates):
                c[y_idx(s, k)] = (
                    cand.site_cost_eur + cand.cut_excess_m3 * dump + cand.fill_need_m3 * gravel
                )
        for i in range(n):
            for j in range(n):
                if allowed[i][j]:
                    c[t_idx(i, j)] = self.config.cost_per_m3_km * distances[i][j] - dump - gravel

        lb = np.zeros(num_vars)
        ub = np.ones(num_vars)
        for i in range(n):
            for j in range(n):
                idx = t_idx(i, j)
                ub[idx] = np.inf if allowed[i][j] else 0.0
        bounds = Bounds(lb, ub)
        integrality = np.zeros(num_vars)
        integrality[:num_y] = 1

        constraints = []
        for s in range(n):
            row = np.zeros(num_vars)
            for k in range(cand_counts[s]):
                row[y_idx(s, k)] = 1.0
            constraints.append(LinearConstraint(row, lb=1, ub=1))
        for i in range(n):
            row = np.zeros(num_vars)
            for j in range(n):
                if allowed[i][j]:
                    row[t_idx(i, j)] = 1.0
            for k, cand in enumerate(sites[i].candidates):
                row[y_idx(i, k)] = -cand.cut_excess_m3
            constraints.append(LinearConstraint(row, lb=-np.inf, ub=0))
        for j in range(n):
            row = np.zeros(num_vars)
            for i in range(n):
                if allowed[i][j]:
                    row[t_idx(i, j)] = 1.0
            for k, cand in enumerate(sites[j].candidates):
                row[y_idx(j, k)] = -cand.fill_need_m3
            constraints.append(LinearConstraint(row, lb=-np.inf, ub=0))

        result = milp(c, constraints=constraints, integrality=integrality, bounds=bounds)
        sol = ParkMILPSolution(
            solver_status=result.message or ("ok" if result.success else "failed")
        )
        if not result.success or result.x is None:
            return sol

        x = result.x
        for s in range(n):
            best_k, best_val = 0, -1.0
            for k in range(cand_counts[s]):
                val = x[y_idx(s, k)]
                if val > best_val:
                    best_val, best_k = val, k
            sol.chosen_index[sites[s].site_id] = best_k
            sol.chosen_candidate[sites[s].site_id] = sites[s].candidates[best_k]

        consumed_out = [0.0] * n
        consumed_in = [0.0] * n
        for i in range(n):
            for j in range(n):
                vol = float(x[t_idx(i, j)])
                if vol <= 1e-6:
                    continue
                consumed_out[i] += vol
                consumed_in[j] += vol
                t_cost = self.config.cost_per_m3_km * distances[i][j] * vol
                sol.flows.append(
                    TransportFlow(
                        sites[i].site_id, sites[j].site_id, vol, distances[i][j], t_cost
                    )
                )
        sol.total_transport_eur = sum(f.transport_cost_eur for f in sol.flows)
        for s in range(n):
            cand = sol.chosen_candidate[sites[s].site_id]
            sol.total_site_cost_eur += cand.site_cost_eur
            residual_dump = max(0.0, cand.cut_excess_m3 - consumed_out[s])
            sol.residual_dump_m3[sites[s].site_id] = residual_dump
            sol.total_dump_eur += residual_dump * dump
            residual_gravel = max(0.0, cand.fill_need_m3 - consumed_in[s])
            sol.residual_gravel_m3[sites[s].site_id] = residual_gravel
            sol.total_gravel_eur += residual_gravel * gravel
        return sol
