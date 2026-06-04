"""
Park-wide Earthwork Optimizer for Wind Turbine Earthwork Calculator V2

Given multiple wind turbine sites in the same park with surplus (cut) at some
sites and deficit (fill) at others, this module solves the **material transport
problem**: how much earth to haul from each surplus site to each deficit site
so that the park-wide total cost (transport + remaining disposal + remaining
external gravel) is minimised.

Two solvers are provided (see `docs/plans/V3_ROADMAP.md` Section #2):

  - ``ParkOptimizer.solve()`` — transport-only LP (scipy.optimize.linprog).
    Each site has a single fixed cut/fill balance; only the haul plan is
    optimised.
  - ``ParkOptimizer.solve_milp()`` — joint MILP (scipy.optimize.milp). Each
    site offers several platform-height *candidates* (different cut/fill
    balances + intrinsic cost); the solver picks one candidate per site AND
    the transport plan together, minimising true park-wide total cost.

The core math is QGIS-independent; the result data classes can be fed into the
existing report generators.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Optional, Sequence


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SiteEarthwork:
    """Net earthwork balance at a single site for a chosen platform height."""

    site_id: str
    x: float                     # easting (m, e.g. UTM 32N)
    y: float                     # northing (m)
    cut_excess_m3: float = 0.0   # surplus that would otherwise be dumped
    fill_need_m3: float = 0.0    # deficit that would otherwise need imported gravel

    def __post_init__(self) -> None:
        if self.cut_excess_m3 < 0 or self.fill_need_m3 < 0:
            raise ValueError(
                f"cut_excess and fill_need must be non-negative; got "
                f"cut={self.cut_excess_m3}, fill={self.fill_need_m3}"
            )


@dataclass(frozen=True)
class SiteCandidate:
    """One platform-height option for a site, with its earthwork balance.

    `site_cost_eur` is the intrinsic cost of choosing this candidate (e.g.
    excavation + platform construction at that height), excluding dump and
    external-gravel costs — those are derived from cut/fill in the MILP
    objective so that transport savings are accounted for consistently.
    """

    cut_excess_m3: float
    fill_need_m3: float
    site_cost_eur: float = 0.0
    label: str = ""

    def __post_init__(self) -> None:
        if self.cut_excess_m3 < 0 or self.fill_need_m3 < 0:
            raise ValueError(
                f"cut_excess and fill_need must be non-negative; got "
                f"cut={self.cut_excess_m3}, fill={self.fill_need_m3}"
            )


@dataclass(frozen=True)
class SiteWithCandidates:
    """A site location plus the set of platform-height candidates to choose from."""

    site_id: str
    x: float
    y: float
    candidates: Sequence[SiteCandidate]

    def __post_init__(self) -> None:
        if not self.candidates:
            raise ValueError(f"site {self.site_id} has no candidates")


@dataclass(frozen=True)
class TransportConfig:
    """Cost parameters for material transport between sites."""

    cost_per_m3_km: float        # €/(m³·km), e.g. 0.20
    dump_cost_per_m3: float      # €/m³ for disposing of cut at the source site
    external_gravel_cost_per_m3: float  # €/m³ for importing fill from outside
    max_distance_km: Optional[float] = None  # forbids transport beyond this distance


@dataclass(frozen=True)
class TransportFlow:
    """How many m³ flow from one site to another."""

    from_site: str
    to_site: str
    volume_m3: float
    distance_km: float
    transport_cost_eur: float


@dataclass
class ParkSolution:
    """Result of the park-wide transport optimisation."""

    flows: list[TransportFlow] = field(default_factory=list)
    residual_dump_m3: dict[str, float] = field(default_factory=dict)
    residual_gravel_m3: dict[str, float] = field(default_factory=dict)
    total_transport_eur: float = 0.0
    total_dump_eur: float = 0.0
    total_gravel_eur: float = 0.0
    baseline_cost_eur: float = 0.0   # cost if every site handled cut/fill alone
    savings_eur: float = 0.0         # baseline_cost - (transport + dump + gravel)
    solver_status: str = ""          # e.g. "optimal", "infeasible"

    @property
    def total_cost_eur(self) -> float:
        return self.total_transport_eur + self.total_dump_eur + self.total_gravel_eur


@dataclass
class ParkMILPSolution:
    """Result of the joint candidate-selection + transport optimisation."""

    chosen_index: dict[str, int] = field(default_factory=dict)       # site_id -> candidate index
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
        return (self.total_site_cost_eur + self.total_transport_eur
                + self.total_dump_eur + self.total_gravel_eur)


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------


def euclidean_distance_km(a, b) -> float:
    """Distance in km between two sites (coordinates in metres).

    Accepts any objects with ``.x`` and ``.y`` attributes (SiteEarthwork or
    SiteWithCandidates).
    """
    return math.hypot(a.x - b.x, a.y - b.y) / 1000.0


# ---------------------------------------------------------------------------
# Optimizer
# ---------------------------------------------------------------------------


class ParkOptimizer:
    """Solves the park-wide transport problem with a LP.

    Variables: ``t[i, j] >= 0``, m³ transported from site ``i`` to site ``j``.

    Constraints:
      - ``sum_j t[i, j] <= cut_excess[i]``     (can't export more than you cut)
      - ``sum_i t[i, j] <= fill_need[j]``      (can't import more than is needed)
      - ``t[i, j] = 0`` if ``distance(i, j) > max_distance_km``

    Objective per m³ of flow:
      ``cost_per_m3 = transport_cost_per_m3_km * distance(i, j)
                       - dump_cost_per_m3
                       - external_gravel_cost_per_m3``

    The dump/gravel terms are subtracted because moving 1 m³ from i→j *saves*
    both a dump at i and a gravel import at j. If the saved cost exceeds the
    transport cost, the LP will move material; otherwise it will leave residual
    cut and fill to be paid at the baseline rates.
    """

    def __init__(
        self,
        config: TransportConfig,
        distance_fn: Callable[[SiteEarthwork, SiteEarthwork], float] = euclidean_distance_km,
    ):
        self.config = config
        self.distance_fn = distance_fn

    def solve(self, sites: Sequence[SiteEarthwork]) -> ParkSolution:
        """Run the LP and return the optimal transport plan."""
        if not sites:
            return ParkSolution(solver_status="empty input")

        try:
            from scipy.optimize import linprog
        except ImportError as exc:
            raise ImportError(
                "scipy is required for ParkOptimizer.solve(). It is usually shipped "
                "with QGIS; install via `pip install scipy` if running outside QGIS."
            ) from exc

        n = len(sites)
        # Variables: flat array of size n*n; t[i,j] is at index i*n + j
        num_vars = n * n

        # Pre-compute distances and skip i==j and over-distance pairs.
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

        # Objective coefficients (€ per m³ for each i→j flow).
        c_coeff = [0.0] * num_vars
        saved_per_m3 = (
            self.config.dump_cost_per_m3
            + self.config.external_gravel_cost_per_m3
        )
        for i in range(n):
            for j in range(n):
                idx = i * n + j
                if not allowed[i][j]:
                    # Pin disallowed flows to 0 via upper bound; coefficient irrelevant.
                    c_coeff[idx] = 0.0
                    continue
                transport_cost = self.config.cost_per_m3_km * distances[i][j]
                c_coeff[idx] = transport_cost - saved_per_m3

        # Bounds: 0 <= t[i,j], with disallowed pairs upper-bounded to 0.
        bounds: list[tuple[float, Optional[float]]] = []
        for i in range(n):
            for j in range(n):
                if allowed[i][j]:
                    bounds.append((0.0, None))
                else:
                    bounds.append((0.0, 0.0))

        # Inequality constraints A_ub @ x <= b_ub
        a_ub: list[list[float]] = []
        b_ub: list[float] = []

        # Row per source site: sum_j t[i,j] <= cut_excess[i]
        for i, src in enumerate(sites):
            row = [0.0] * num_vars
            for j in range(n):
                row[i * n + j] = 1.0
            a_ub.append(row)
            b_ub.append(src.cut_excess_m3)

        # Row per destination site: sum_i t[i,j] <= fill_need[j]
        for j, dst in enumerate(sites):
            row = [0.0] * num_vars
            for i in range(n):
                row[i * n + j] = 1.0
            a_ub.append(row)
            b_ub.append(dst.fill_need_m3)

        result = linprog(
            c=c_coeff,
            A_ub=a_ub,
            b_ub=b_ub,
            bounds=bounds,
            method="highs",
        )

        solution = ParkSolution(solver_status=result.message or ("ok" if result.success else "failed"))
        if not result.success:
            return solution

        # Build flow list and residuals.
        flows: list[TransportFlow] = []
        consumed_out = [0.0] * n
        consumed_in = [0.0] * n
        x = result.x
        for i in range(n):
            for j in range(n):
                vol = float(x[i * n + j])
                if vol <= 1e-6:
                    continue
                consumed_out[i] += vol
                consumed_in[j] += vol
                t_cost = self.config.cost_per_m3_km * distances[i][j] * vol
                flows.append(TransportFlow(
                    from_site=sites[i].site_id,
                    to_site=sites[j].site_id,
                    volume_m3=vol,
                    distance_km=distances[i][j],
                    transport_cost_eur=t_cost,
                ))

        solution.flows = flows
        solution.total_transport_eur = sum(f.transport_cost_eur for f in flows)

        # Residual cut (not transported away) → still must be dumped.
        for i, s in enumerate(sites):
            residual = max(0.0, s.cut_excess_m3 - consumed_out[i])
            solution.residual_dump_m3[s.site_id] = residual
            solution.total_dump_eur += residual * self.config.dump_cost_per_m3

        # Residual fill (not covered by transport) → still must be imported.
        for j, s in enumerate(sites):
            residual = max(0.0, s.fill_need_m3 - consumed_in[j])
            solution.residual_gravel_m3[s.site_id] = residual
            solution.total_gravel_eur += residual * self.config.external_gravel_cost_per_m3

        # Baseline: every site handles its own cut/fill independently.
        baseline = sum(
            s.cut_excess_m3 * self.config.dump_cost_per_m3
            + s.fill_need_m3 * self.config.external_gravel_cost_per_m3
            for s in sites
        )
        solution.baseline_cost_eur = baseline
        solution.savings_eur = baseline - solution.total_cost_eur

        return solution

    def solve_milp(self, sites: Sequence[SiteWithCandidates]) -> ParkMILPSolution:
        """Jointly choose one platform-height candidate per site and the optimal
        material transport plan, minimising park-wide total cost.

        Variables:
          - ``y[s, k] in {0, 1}`` — candidate k chosen for site s
          - ``t[i, j] >= 0`` — m³ transported from site i to site j

        Constraints:
          - exactly one candidate per site: ``sum_k y[s, k] == 1``
          - export bounded by chosen cut: ``sum_j t[i, j] <= sum_k y[i, k]·cut[i, k]``
          - import bounded by chosen fill: ``sum_i t[i, j] <= sum_k y[j, k]·fill[j, k]``
          - ``t[i, j] = 0`` for i == j or distance > max_distance_km

        Objective (true total cost):
          ``y[s, k]`` coeff = ``site_cost[s, k] + cut·dump + fill·gravel``
          ``t[i, j]`` coeff = ``transport_cost·distance - dump - gravel``
        The transport term claws back the dump+gravel cost that is otherwise
        charged on the chosen candidate's full cut/fill.
        """
        if not sites:
            return ParkMILPSolution(solver_status="empty input")

        try:
            import numpy as np
            from scipy.optimize import milp, LinearConstraint, Bounds
        except ImportError as exc:
            raise ImportError(
                "scipy>=1.9 (with optimize.milp) and numpy are required for "
                "ParkOptimizer.solve_milp(); both ship with QGIS."
            ) from exc

        n = len(sites)
        cand_counts = [len(s.candidates) for s in sites]
        num_y = sum(cand_counts)

        # y index map: y_offset[s] is the start index of site s's candidate vars.
        y_offset = [0] * n
        acc = 0
        for s in range(n):
            y_offset[s] = acc
            acc += cand_counts[s]

        def y_idx(s: int, k: int) -> int:
            return y_offset[s] + k

        def t_idx(i: int, j: int) -> int:
            return num_y + i * n + j

        num_t = n * n
        num_vars = num_y + num_t

        dump = self.config.dump_cost_per_m3
        gravel = self.config.external_gravel_cost_per_m3

        # Distances + allowed transport pairs.
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

        # Objective coefficients.
        c = np.zeros(num_vars)
        for s in range(n):
            for k, cand in enumerate(sites[s].candidates):
                c[y_idx(s, k)] = (
                    cand.site_cost_eur
                    + cand.cut_excess_m3 * dump
                    + cand.fill_need_m3 * gravel
                )
        for i in range(n):
            for j in range(n):
                if allowed[i][j]:
                    c[t_idx(i, j)] = self.config.cost_per_m3_km * distances[i][j] - dump - gravel

        # Bounds: y in [0, 1]; t in [0, inf) if allowed else [0, 0].
        lb = np.zeros(num_vars)
        ub = np.ones(num_vars)  # y upper = 1
        for i in range(n):
            for j in range(n):
                idx = t_idx(i, j)
                ub[idx] = np.inf if allowed[i][j] else 0.0
        bounds = Bounds(lb, ub)

        # Integrality: 1 for y (binary), 0 for t (continuous).
        integrality = np.zeros(num_vars)
        integrality[:num_y] = 1

        constraints = []

        # 1. Exactly one candidate per site.
        for s in range(n):
            row = np.zeros(num_vars)
            for k in range(cand_counts[s]):
                row[y_idx(s, k)] = 1.0
            constraints.append(LinearConstraint(row, lb=1, ub=1))

        # 2. Export <= chosen cut:  sum_j t[i,j] - sum_k y[i,k]·cut[i,k] <= 0
        for i in range(n):
            row = np.zeros(num_vars)
            for j in range(n):
                if allowed[i][j]:
                    row[t_idx(i, j)] = 1.0
            for k, cand in enumerate(sites[i].candidates):
                row[y_idx(i, k)] = -cand.cut_excess_m3
            constraints.append(LinearConstraint(row, lb=-np.inf, ub=0))

        # 3. Import <= chosen fill:  sum_i t[i,j] - sum_k y[j,k]·fill[j,k] <= 0
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

        # Recover chosen candidate per site (highest y[s,k], should be ~1).
        for s in range(n):
            best_k, best_val = 0, -1.0
            for k in range(cand_counts[s]):
                val = x[y_idx(s, k)]
                if val > best_val:
                    best_val, best_k = val, k
            sol.chosen_index[sites[s].site_id] = best_k
            sol.chosen_candidate[sites[s].site_id] = sites[s].candidates[best_k]

        # Build flows + consumed totals.
        consumed_out = [0.0] * n
        consumed_in = [0.0] * n
        flows: list[TransportFlow] = []
        for i in range(n):
            for j in range(n):
                vol = float(x[t_idx(i, j)])
                if vol <= 1e-6:
                    continue
                consumed_out[i] += vol
                consumed_in[j] += vol
                t_cost = self.config.cost_per_m3_km * distances[i][j] * vol
                flows.append(TransportFlow(
                    from_site=sites[i].site_id,
                    to_site=sites[j].site_id,
                    volume_m3=vol,
                    distance_km=distances[i][j],
                    transport_cost_eur=t_cost,
                ))
        sol.flows = flows
        sol.total_transport_eur = sum(f.transport_cost_eur for f in flows)

        # Site costs + residual dump/gravel based on chosen candidates.
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
