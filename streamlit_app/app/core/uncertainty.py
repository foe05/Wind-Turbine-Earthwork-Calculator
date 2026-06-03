"""
Monte-Carlo-Unsicherheits-Analyse (MVP-Port aus core/uncertainty.py).

Latin Hypercube Sampling + normalverteilte Parameter; per-Output-Statistiken
(Mittel, Std, 5/25/50/75/95-Perzentile, CV); Sensitivitätsanalyse über
Korrelation und linearen Slope.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import numpy as np

try:
    from scipy.stats import qmc

    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class TerrainType(str, Enum):
    FLAT = "flat"
    MODERATE = "moderate"
    STEEP = "steep"


_DEM_STD_BY_TERRAIN = {
    TerrainType.FLAT: 0.075,
    TerrainType.MODERATE: 0.10,
    TerrainType.STEEP: 0.15,
}


@dataclass
class UncertaintyConfig:
    dem_vertical_std: float = 0.075
    fok_std: float = 0.0
    foundation_depth_std: float = 0.1
    gravel_thickness_std: float = 0.05
    slope_angle_std: float = 3.0
    num_samples: int = 1000
    use_latin_hypercube: bool = True
    random_seed: Optional[int] = None
    terrain_type: TerrainType = TerrainType.FLAT

    @classmethod
    def for_terrain(cls, terrain_type: TerrainType, **kwargs) -> "UncertaintyConfig":
        kwargs.setdefault("dem_vertical_std", _DEM_STD_BY_TERRAIN[terrain_type])
        kwargs["terrain_type"] = terrain_type
        return cls(**kwargs)


@dataclass
class UncertaintyResult:
    mean: float
    std: float
    percentile_5: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_95: float
    min_value: float
    max_value: float
    coefficient_of_variation: float
    samples: np.ndarray

    @classmethod
    def from_samples(cls, samples: np.ndarray) -> "UncertaintyResult":
        samples = np.asarray(samples, dtype=float)
        mean = float(samples.mean())
        std = float(samples.std())
        cv = std / abs(mean) if abs(mean) > 1e-10 else (0.0 if std < 1e-10 else float("inf"))
        return cls(
            mean=mean,
            std=std,
            percentile_5=float(np.percentile(samples, 5)),
            percentile_25=float(np.percentile(samples, 25)),
            percentile_50=float(np.percentile(samples, 50)),
            percentile_75=float(np.percentile(samples, 75)),
            percentile_95=float(np.percentile(samples, 95)),
            min_value=float(samples.min()),
            max_value=float(samples.max()),
            coefficient_of_variation=cv,
            samples=samples,
        )

    def ci_90(self) -> tuple[float, float]:
        return (self.percentile_5, self.percentile_95)

    def ci_50(self) -> tuple[float, float]:
        return (self.percentile_25, self.percentile_75)

    def to_dict(self) -> dict:
        return {
            "mean": round(self.mean, 3),
            "std": round(self.std, 3),
            "p5": round(self.percentile_5, 3),
            "p25": round(self.percentile_25, 3),
            "p50": round(self.percentile_50, 3),
            "p75": round(self.percentile_75, 3),
            "p95": round(self.percentile_95, 3),
            "min": round(self.min_value, 3),
            "max": round(self.max_value, 3),
            "cv": round(self.coefficient_of_variation, 4),
            "n_samples": len(self.samples),
        }


@dataclass
class SensitivityResult:
    parameter_name: str
    correlation: float
    linear_slope: float

    def to_dict(self) -> dict:
        return {
            "parameter": self.parameter_name,
            "correlation": round(self.correlation, 4),
            "linear_slope": round(self.linear_slope, 4),
            "abs_correlation": round(abs(self.correlation), 4),
        }


@dataclass
class UncertaintyAnalysisResult:
    config: UncertaintyConfig
    outputs: dict[str, UncertaintyResult] = field(default_factory=dict)
    sensitivities: dict[str, dict[str, SensitivityResult]] = field(default_factory=dict)
    parameter_samples: dict[str, np.ndarray] = field(default_factory=dict)
    output_samples: dict[str, np.ndarray] = field(default_factory=dict)
    num_samples: int = 0
    computation_time_s: float = 0.0

    def get_sensitivity_ranking(self, output_name: str) -> list[tuple[str, float]]:
        if output_name not in self.sensitivities:
            return []
        ranking = [
            (name, abs(r.correlation))
            for name, r in self.sensitivities[output_name].items()
        ]
        ranking.sort(key=lambda x: x[1], reverse=True)
        return ranking

    def to_dict(self) -> dict:
        return {
            "config": {
                "terrain_type": self.config.terrain_type.value,
                "num_samples": self.config.num_samples,
                "use_latin_hypercube": self.config.use_latin_hypercube,
                "dem_vertical_std": self.config.dem_vertical_std,
                "fok_std": self.config.fok_std,
                "foundation_depth_std": self.config.foundation_depth_std,
                "gravel_thickness_std": self.config.gravel_thickness_std,
                "slope_angle_std": self.config.slope_angle_std,
            },
            "outputs": {k: v.to_dict() for k, v in self.outputs.items()},
            "sensitivities": {
                output_name: {p: s.to_dict() for p, s in params.items()}
                for output_name, params in self.sensitivities.items()
            },
            "num_samples": self.num_samples,
            "computation_time_s": round(self.computation_time_s, 2),
        }


def sample_parameters(
    config: UncertaintyConfig, base_values: dict[str, float]
) -> dict[str, np.ndarray]:
    """Latin-Hypercube oder Random Sampling normalverteilter Parameter."""
    specs: list[tuple[str, float, float]] = []
    # (name, mean, std) — nur Parameter mit positivem std werden propagiert
    if config.dem_vertical_std > 0:
        specs.append(("dem_bias", 0.0, config.dem_vertical_std))
    if config.fok_std > 0:
        specs.append(("fok", base_values.get("fok", 0.0), config.fok_std))
    if config.foundation_depth_std > 0:
        specs.append(
            ("foundation_depth", base_values.get("foundation_depth", 0.0), config.foundation_depth_std)
        )
    if config.gravel_thickness_std > 0:
        specs.append(
            ("gravel_thickness", base_values.get("gravel_thickness", 0.0), config.gravel_thickness_std)
        )
    if config.slope_angle_std > 0:
        specs.append(("slope_angle", base_values.get("slope_angle", 45.0), config.slope_angle_std))

    if not specs:
        return {}

    n = config.num_samples
    d = len(specs)
    if config.use_latin_hypercube and HAS_SCIPY:
        sampler = qmc.LatinHypercube(d=d, seed=config.random_seed)
        u = sampler.random(n)
    else:
        rng = np.random.default_rng(config.random_seed)
        u = rng.random((n, d))

    # Uniform [0,1] → normal via inverse-CDF
    # Vermeidung von 0/1 zur numerischen Stabilität
    u = np.clip(u, 1e-9, 1.0 - 1e-9)
    z = np.sqrt(2) * _erfinv(2 * u - 1)

    samples: dict[str, np.ndarray] = {}
    for i, (name, mean, std) in enumerate(specs):
        samples[name] = mean + std * z[:, i]
    return samples


def _erfinv(x: np.ndarray) -> np.ndarray:
    """Approximation des inversen Fehlerintegrals (für numpy-Arrays)."""
    # Verwende scipy falls verfügbar
    try:
        from scipy.special import erfinv

        return erfinv(x)
    except ImportError:
        # Winitzki-Approximation
        a = 0.147
        ln = np.log(1 - x * x)
        first = 2 / (math.pi * a) + ln / 2
        return np.sign(x) * np.sqrt(np.sqrt(first * first - ln / a) - first)


def run_uncertainty_analysis(
    config: UncertaintyConfig,
    base_values: dict[str, float],
    evaluate: Callable[[dict[str, float]], dict[str, float]],
    output_names: Optional[list[str]] = None,
) -> UncertaintyAnalysisResult:
    """Monte-Carlo-Lauf über ``evaluate(perturbed_params) -> outputs``.

    Args:
        config: Sampling-Konfiguration.
        base_values: Nominalwerte aller Parameter (auch der ohne Unsicherheit).
        evaluate: Callback, der ein perturbierten Parameter-Dict bekommt und
            ein Dict numerischer Outputs zurückgibt.
        output_names: Optional Filter, welche Outputs ausgewertet werden.

    Returns:
        UncertaintyAnalysisResult mit Verteilungen + Sensitivitäten.
    """
    t0 = time.time()
    param_samples = sample_parameters(config, base_values)
    n = config.num_samples
    all_outputs: dict[str, list[float]] = {}

    for i in range(n):
        perturbed = dict(base_values)
        for name, arr in param_samples.items():
            if name == "dem_bias":
                # bias als Offset zur DEM-Höhe (kein direkter Parameter)
                perturbed["dem_bias"] = float(arr[i])
            else:
                perturbed[name] = float(arr[i])
        try:
            out = evaluate(perturbed)
        except Exception:
            continue
        for k, v in out.items():
            if output_names and k not in output_names:
                continue
            all_outputs.setdefault(k, []).append(float(v))

    result = UncertaintyAnalysisResult(config=config, num_samples=n)
    result.parameter_samples = param_samples
    for name, vals in all_outputs.items():
        arr = np.array(vals)
        result.output_samples[name] = arr
        result.outputs[name] = UncertaintyResult.from_samples(arr)

    # Sensitivitäten via Korrelation und linearer Regression
    for output_name, output_arr in result.output_samples.items():
        sens: dict[str, SensitivityResult] = {}
        # Output kann kürzer als Sample-Anzahl sein (falls evaluate Fehler hatte)
        n_eff = len(output_arr)
        for param_name, param_arr in param_samples.items():
            par = param_arr[:n_eff]
            if len(par) < 2 or par.std() < 1e-10:
                continue
            corr = float(np.corrcoef(par, output_arr)[0, 1])
            corr = 0.0 if np.isnan(corr) else corr
            slope = float(np.polyfit(par, output_arr, 1)[0])
            sens[param_name] = SensitivityResult(
                parameter_name=param_name,
                correlation=corr,
                linear_slope=slope,
            )
        result.sensitivities[output_name] = sens

    result.computation_time_s = time.time() - t0
    return result
