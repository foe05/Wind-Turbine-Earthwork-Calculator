"""
Uncertainty Propagation Module for Wind Turbine Earthwork Calculator

Implements Monte Carlo simulation with Latin Hypercube Sampling and
Sobol sensitivity analysis for uncertainty quantification.

DEM accuracy based on official German standards:
- Flat terrain: ±10cm + 5% of grid size (1m) = ±15cm at 95% (2σ) → σ ≈ 7.5cm
- Steep terrain with vegetation: ±10cm + 20% of grid size = ±30cm at 95% (2σ) → σ ≈ 15cm

Author: Wind Energy Site Planning
Version: 2.0 - Uncertainty Extension
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
import numpy as np
import copy
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed

try:
    from scipy.stats import qmc, norm
    from scipy.stats.qmc import Sobol
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

from .surface_types import MultiSurfaceCalculationResult


class TerrainType(Enum):
    """Terrain type for DEM uncertainty estimation."""
    FLAT = "flat"           # Flat to slightly sloped, open terrain
    MODERATE = "moderate"   # Moderate slope or some vegetation
    STEEP = "steep"         # Steep terrain with dense vegetation


@dataclass
class UncertaintyConfig:
    """
    Configuration for uncertainty propagation analysis.

    All standard deviations (σ) represent 1σ values.
    DEM uncertainty values based on German hoehendaten.de specifications.

    Attributes:
        dem_vertical_std: DEM vertical uncertainty (1σ in meters)
            - Flat terrain: 0.075m (derived from ±15cm at 2σ)
            - Moderate: 0.10m
            - Steep with vegetation: 0.15m (derived from ±30cm at 2σ)
        dem_systematic_bias: Systematic DEM bias (meters), usually 0
        fok_std: FOK (Fundamentoberkante) uncertainty (1σ in meters)
            Default 0 because FOK is surveyor-specified and must be maintained
        foundation_depth_std: Foundation depth uncertainty (1σ in meters)
        gravel_thickness_std: Gravel layer thickness uncertainty (1σ in meters)
        slope_angle_std: Embankment slope angle uncertainty (1σ in degrees)
        boom_slope_std: Boom surface slope uncertainty (1σ in percent)
        rotor_offset_std: Rotor storage height offset uncertainty (1σ in meters)
        polygon_position_std: Geometry positioning uncertainty (1σ in meters)
        num_samples: Number of Monte Carlo samples
        use_latin_hypercube: Use Latin Hypercube Sampling instead of random
        random_seed: Random seed for reproducibility (None for random)
        terrain_type: Terrain type for automatic DEM uncertainty selection
    """
    # DEM uncertainty - based on official German DEM specifications
    # Values are 1σ (derived from 2σ specifications)
    dem_vertical_std: float = 0.075  # Default for flat terrain
    dem_systematic_bias: float = 0.0

    # Planning parameters
    # FOK default 0 because it's surveyor-specified and must be maintained
    fok_std: float = 0.0
    foundation_depth_std: float = 0.1
    gravel_thickness_std: float = 0.05

    # Geotechnical parameters
    slope_angle_std: float = 3.0  # degrees

    # Surface-specific parameters
    boom_slope_std: float = 0.5  # percent
    rotor_offset_std: float = 0.05  # meters

    # Geometry uncertainty (CAD accuracy)
    polygon_position_std: float = 0.0  # meters, usually very accurate

    # Monte Carlo configuration
    num_samples: int = 1000
    use_latin_hypercube: bool = True
    random_seed: Optional[int] = None

    # Terrain type for automatic DEM uncertainty
    terrain_type: TerrainType = TerrainType.FLAT

    def __post_init__(self):
        """Set DEM uncertainty based on terrain type if using default."""
        if self.dem_vertical_std == 0.075:  # Default value
            if self.terrain_type == TerrainType.FLAT:
                self.dem_vertical_std = 0.075  # ±15cm at 2σ → σ = 7.5cm
            elif self.terrain_type == TerrainType.MODERATE:
                self.dem_vertical_std = 0.10   # Intermediate
            elif self.terrain_type == TerrainType.STEEP:
                self.dem_vertical_std = 0.15   # ±30cm at 2σ → σ = 15cm

    @classmethod
    def for_terrain(cls, terrain_type: TerrainType, **kwargs) -> 'UncertaintyConfig':
        """
        Create configuration with appropriate DEM uncertainty for terrain type.

        Args:
            terrain_type: Type of terrain
            **kwargs: Override other parameters

        Returns:
            UncertaintyConfig with terrain-appropriate DEM uncertainty
        """
        dem_std_map = {
            TerrainType.FLAT: 0.075,
            TerrainType.MODERATE: 0.10,
            TerrainType.STEEP: 0.15,
        }

        config = cls(
            dem_vertical_std=dem_std_map[terrain_type],
            terrain_type=terrain_type,
            **kwargs
        )
        return config

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'dem_vertical_std': self.dem_vertical_std,
            'dem_systematic_bias': self.dem_systematic_bias,
            'fok_std': self.fok_std,
            'foundation_depth_std': self.foundation_depth_std,
            'gravel_thickness_std': self.gravel_thickness_std,
            'slope_angle_std': self.slope_angle_std,
            'boom_slope_std': self.boom_slope_std,
            'rotor_offset_std': self.rotor_offset_std,
            'polygon_position_std': self.polygon_position_std,
            'num_samples': self.num_samples,
            'use_latin_hypercube': self.use_latin_hypercube,
            'random_seed': self.random_seed,
            'terrain_type': self.terrain_type.value,
        }


@dataclass
class UncertaintyResult:
    """
    Statistical results for a single uncertain output variable.

    Attributes:
        mean: Mean value across all samples
        std: Standard deviation
        percentile_5: 5th percentile (lower bound of 90% CI)
        percentile_25: 25th percentile (Q1)
        percentile_50: 50th percentile (median)
        percentile_75: 75th percentile (Q3)
        percentile_95: 95th percentile (upper bound of 90% CI)
        min_value: Minimum value observed
        max_value: Maximum value observed
        coefficient_of_variation: CV = std / |mean| (relative uncertainty)
        samples: All sample values for histogram/distribution analysis
    """
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
    def from_samples(cls, samples: np.ndarray, name: str = "") -> 'UncertaintyResult':
        """
        Create UncertaintyResult from array of samples.

        Args:
            samples: Array of sample values
            name: Optional name for logging

        Returns:
            UncertaintyResult with computed statistics
        """
        samples = np.array(samples)
        mean = float(np.mean(samples))
        std = float(np.std(samples))

        # Coefficient of variation (handle zero mean)
        if abs(mean) > 1e-10:
            cv = std / abs(mean)
        else:
            cv = 0.0 if std < 1e-10 else float('inf')

        return cls(
            mean=mean,
            std=std,
            percentile_5=float(np.percentile(samples, 5)),
            percentile_25=float(np.percentile(samples, 25)),
            percentile_50=float(np.percentile(samples, 50)),
            percentile_75=float(np.percentile(samples, 75)),
            percentile_95=float(np.percentile(samples, 95)),
            min_value=float(np.min(samples)),
            max_value=float(np.max(samples)),
            coefficient_of_variation=cv,
            samples=samples
        )

    def confidence_interval_90(self) -> Tuple[float, float]:
        """Return 90% confidence interval (5th to 95th percentile)."""
        return (self.percentile_5, self.percentile_95)

    def confidence_interval_50(self) -> Tuple[float, float]:
        """Return 50% confidence interval (25th to 75th percentile)."""
        return (self.percentile_25, self.percentile_75)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without samples for smaller size)."""
        return {
            'mean': round(self.mean, 3),
            'std': round(self.std, 3),
            'percentile_5': round(self.percentile_5, 3),
            'percentile_25': round(self.percentile_25, 3),
            'percentile_50': round(self.percentile_50, 3),
            'percentile_75': round(self.percentile_75, 3),
            'percentile_95': round(self.percentile_95, 3),
            'min': round(self.min_value, 3),
            'max': round(self.max_value, 3),
            'cv': round(self.coefficient_of_variation, 4),
            'n_samples': len(self.samples),
        }

    def format_summary(self, unit: str = "", decimals: int = 2) -> str:
        """
        Format a human-readable summary string.

        Args:
            unit: Unit string (e.g., "m³", "m")
            decimals: Number of decimal places

        Returns:
            Formatted string like "5,243.2 ± 412.5 m³ (CV: 7.9%)"
        """
        fmt = f",.{decimals}f"
        mean_str = f"{self.mean:{fmt}}"
        std_str = f"{self.std:{fmt}}"
        cv_pct = self.coefficient_of_variation * 100

        return f"{mean_str} ± {std_str} {unit} (CV: {cv_pct:.1f}%)"

    def format_confidence_interval(self, unit: str = "", decimals: int = 2) -> str:
        """
        Format 90% confidence interval.

        Args:
            unit: Unit string
            decimals: Number of decimal places

        Returns:
            Formatted string like "90% CI: [4,530, 6,085] m³"
        """
        fmt = f",.{decimals}f"
        return f"90% CI: [{self.percentile_5:{fmt}}, {self.percentile_95:{fmt}}] {unit}"


@dataclass
class SensitivityResult:
    """
    Results from sensitivity analysis for a single parameter.

    Attributes:
        parameter_name: Name of the input parameter
        parameter_values: Array of tested parameter values
        output_values: Corresponding output values
        sensitivity_index: Sensitivity index (e.g., first-order Sobol index)
        total_sensitivity_index: Total sensitivity index (includes interactions)
        linear_slope: Linear regression slope (output change per unit input change)
        correlation: Pearson correlation coefficient
    """
    parameter_name: str
    parameter_values: np.ndarray
    output_values: np.ndarray
    sensitivity_index: float = 0.0
    total_sensitivity_index: float = 0.0
    linear_slope: float = 0.0
    correlation: float = 0.0

    @classmethod
    def from_samples(cls, name: str, param_values: np.ndarray,
                     output_values: np.ndarray) -> 'SensitivityResult':
        """
        Create SensitivityResult from parameter and output samples.

        Args:
            name: Parameter name
            param_values: Array of parameter values
            output_values: Corresponding output values

        Returns:
            SensitivityResult with computed statistics
        """
        # Linear regression
        if len(param_values) > 1 and np.std(param_values) > 1e-10:
            slope = np.polyfit(param_values, output_values, 1)[0]
            correlation = np.corrcoef(param_values, output_values)[0, 1]
        else:
            slope = 0.0
            correlation = 0.0

        return cls(
            parameter_name=name,
            parameter_values=param_values,
            output_values=output_values,
            linear_slope=float(slope),
            correlation=float(correlation) if not np.isnan(correlation) else 0.0
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without arrays)."""
        return {
            'parameter': self.parameter_name,
            'sensitivity_index': round(self.sensitivity_index, 4),
            'total_sensitivity_index': round(self.total_sensitivity_index, 4),
            'linear_slope': round(self.linear_slope, 4),
            'correlation': round(self.correlation, 4),
        }


@dataclass
class UncertaintyAnalysisResult:
    """
    Complete results from uncertainty propagation analysis.

    Contains distributions for all output variables and sensitivity rankings.

    Attributes:
        config: Configuration used for analysis
        nominal_result: Result from nominal (unperturbed) calculation
        crane_height: Uncertainty in optimal crane height
        total_cut: Uncertainty in total cut volume
        total_fill: Uncertainty in total fill volume
        net_volume: Uncertainty in net volume
        total_volume_moved: Uncertainty in total volume moved
        boom_slope: Uncertainty in optimal boom slope (if optimized)
        rotor_offset: Uncertainty in optimal rotor offset (if optimized)
        sensitivity: Sensitivity results for each input parameter
        parameter_correlations: Correlation matrix between inputs and outputs
        num_samples: Number of Monte Carlo samples run
        computation_time_seconds: Time taken for analysis
    """
    config: UncertaintyConfig
    nominal_result: MultiSurfaceCalculationResult

    # Output uncertainties
    crane_height: UncertaintyResult
    total_cut: UncertaintyResult
    total_fill: UncertaintyResult
    net_volume: UncertaintyResult
    total_volume_moved: UncertaintyResult
    boom_slope: Optional[UncertaintyResult] = None
    rotor_offset: Optional[UncertaintyResult] = None

    # Sensitivity analysis
    sensitivity: Dict[str, SensitivityResult] = field(default_factory=dict)

    # Additional statistics
    parameter_correlations: Optional[np.ndarray] = None
    num_samples: int = 0
    computation_time_seconds: float = 0.0

    # All individual results for detailed analysis
    all_results: List[MultiSurfaceCalculationResult] = field(default_factory=list)

    def get_sensitivity_ranking(self, output_name: str = 'total_volume_moved') -> List[Tuple[str, float]]:
        """
        Get parameters ranked by sensitivity for a specific output.

        Args:
            output_name: Name of output variable

        Returns:
            List of (parameter_name, sensitivity_index) sorted by importance
        """
        if not self.sensitivity:
            return []

        ranking = [
            (name, result.total_sensitivity_index)
            for name, result in self.sensitivity.items()
        ]

        # Sort by absolute sensitivity (descending)
        ranking.sort(key=lambda x: abs(x[1]), reverse=True)

        return ranking

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization and reporting."""
        return {
            'config': self.config.to_dict(),
            'nominal': self.nominal_result.to_dict(),
            'uncertainty': {
                'crane_height': self.crane_height.to_dict(),
                'total_cut': self.total_cut.to_dict(),
                'total_fill': self.total_fill.to_dict(),
                'net_volume': self.net_volume.to_dict(),
                'total_volume_moved': self.total_volume_moved.to_dict(),
                'boom_slope': self.boom_slope.to_dict() if self.boom_slope else None,
                'rotor_offset': self.rotor_offset.to_dict() if self.rotor_offset else None,
            },
            'sensitivity': {
                name: result.to_dict()
                for name, result in self.sensitivity.items()
            },
            'sensitivity_ranking': self.get_sensitivity_ranking(),
            'num_samples': self.num_samples,
            'computation_time_seconds': round(self.computation_time_seconds, 2),
        }

    def format_report(self) -> str:
        """
        Generate formatted text report of uncertainty analysis.

        Returns:
            Multi-line string with formatted results
        """
        lines = []
        lines.append("=" * 70)
        lines.append("UNCERTAINTY PROPAGATION RESULTS")
        lines.append(f"({self.num_samples} Monte Carlo Samples)")
        lines.append("=" * 70)
        lines.append("")

        # Optimal crane height
        lines.append("OPTIMAL CRANE HEIGHT")
        lines.append(f"  {self.crane_height.format_summary('m ü.NN', 2)}")
        lines.append(f"  {self.crane_height.format_confidence_interval('m', 2)}")
        lines.append(f"  Range: [{self.crane_height.min_value:.2f}, {self.crane_height.max_value:.2f}] m")
        lines.append("")

        # Volumes
        lines.append("TOTAL CUT VOLUME")
        lines.append(f"  {self.total_cut.format_summary('m³', 1)}")
        lines.append(f"  {self.total_cut.format_confidence_interval('m³', 0)}")
        lines.append("")

        lines.append("TOTAL FILL VOLUME")
        lines.append(f"  {self.total_fill.format_summary('m³', 1)}")
        lines.append(f"  {self.total_fill.format_confidence_interval('m³', 0)}")
        lines.append("")

        lines.append("NET VOLUME (Cut - Fill)")
        lines.append(f"  {self.net_volume.format_summary('m³', 1)}")
        lines.append(f"  {self.net_volume.format_confidence_interval('m³', 0)}")
        lines.append("")

        lines.append("TOTAL VOLUME MOVED")
        lines.append(f"  {self.total_volume_moved.format_summary('m³', 1)}")
        lines.append(f"  {self.total_volume_moved.format_confidence_interval('m³', 0)}")
        lines.append("")

        # Optional outputs
        if self.boom_slope:
            lines.append("BOOM SLOPE")
            lines.append(f"  {self.boom_slope.format_summary('%', 2)}")
            lines.append("")

        if self.rotor_offset:
            lines.append("ROTOR HEIGHT OFFSET")
            lines.append(f"  {self.rotor_offset.format_summary('m', 3)}")
            lines.append("")

        # Sensitivity ranking
        if self.sensitivity:
            lines.append("=" * 70)
            lines.append("SENSITIVITY ANALYSIS")
            lines.append("=" * 70)
            lines.append("")
            lines.append("Parameter                          Sensitivity   Correlation")
            lines.append("-" * 60)

            ranking = self.get_sensitivity_ranking()
            for param_name, sens_index in ranking:
                result = self.sensitivity[param_name]
                corr = result.correlation
                sens_pct = sens_index * 100

                # Create bar visualization
                bar_len = min(20, int(abs(sens_index) * 20))
                bar = "█" * bar_len

                lines.append(
                    f"  {param_name:<30} {sens_pct:>6.1f}%  {corr:>+.3f}  {bar}"
                )

            lines.append("")

        # Configuration used
        lines.append("=" * 70)
        lines.append("UNCERTAINTY CONFIGURATION")
        lines.append("=" * 70)
        lines.append(f"  DEM vertical std:      {self.config.dem_vertical_std*100:.1f} cm")
        lines.append(f"  FOK std:               {self.config.fok_std*100:.1f} cm")
        lines.append(f"  Foundation depth std:  {self.config.foundation_depth_std*100:.1f} cm")
        lines.append(f"  Gravel thickness std:  {self.config.gravel_thickness_std*100:.1f} cm")
        lines.append(f"  Slope angle std:       {self.config.slope_angle_std:.1f}°")
        lines.append(f"  Terrain type:          {self.config.terrain_type.value}")
        lines.append(f"  Sampling method:       {'Latin Hypercube' if self.config.use_latin_hypercube else 'Random'}")
        lines.append(f"  Computation time:      {self.computation_time_seconds:.1f}s")
        lines.append("")

        return "\n".join(lines)


def generate_parameter_samples(
    config: UncertaintyConfig,
    base_values: Dict[str, float]
) -> Dict[str, np.ndarray]:
    """
    Generate correlated parameter samples using Latin Hypercube Sampling.

    Args:
        config: Uncertainty configuration
        base_values: Dictionary of nominal parameter values

    Returns:
        Dictionary mapping parameter names to sample arrays
    """
    n = config.num_samples

    # Define parameters and their uncertainties
    # Only include parameters with non-zero uncertainty
    param_specs = []

    if config.fok_std > 0:
        param_specs.append(('fok', base_values.get('fok', 0), config.fok_std))

    if config.dem_vertical_std > 0:
        param_specs.append(('dem_noise', 0, config.dem_vertical_std))

    if config.slope_angle_std > 0:
        param_specs.append(('slope_angle', base_values.get('slope_angle', 45), config.slope_angle_std))

    if config.foundation_depth_std > 0:
        param_specs.append(('foundation_depth', base_values.get('foundation_depth', 3.5), config.foundation_depth_std))

    if config.gravel_thickness_std > 0:
        param_specs.append(('gravel_thickness', base_values.get('gravel_thickness', 0.5), config.gravel_thickness_std))

    if config.boom_slope_std > 0:
        param_specs.append(('boom_slope_noise', 0, config.boom_slope_std))

    if config.rotor_offset_std > 0:
        param_specs.append(('rotor_offset_noise', 0, config.rotor_offset_std))

    if len(param_specs) == 0:
        # No uncertainty - return nominal values
        return {name: np.full(n, val) for name, val, _ in [
            ('fok', base_values.get('fok', 0), 0),
            ('slope_angle', base_values.get('slope_angle', 45), 0),
            ('foundation_depth', base_values.get('foundation_depth', 3.5), 0),
            ('gravel_thickness', base_values.get('gravel_thickness', 0.5), 0),
        ]}

    num_params = len(param_specs)

    # Generate uniform samples
    if config.use_latin_hypercube and SCIPY_AVAILABLE:
        # Latin Hypercube Sampling for better coverage
        sampler = qmc.LatinHypercube(d=num_params, seed=config.random_seed)
        uniform_samples = sampler.random(n)
    else:
        # Simple random sampling
        if config.random_seed is not None:
            np.random.seed(config.random_seed)
        uniform_samples = np.random.random((n, num_params))

    # Transform to normal distributions
    samples = {}
    for i, (name, mean, std) in enumerate(param_specs):
        if SCIPY_AVAILABLE:
            samples[name] = norm.ppf(uniform_samples[:, i], mean, std)
        else:
            # Fallback: inverse transform using normal approximation
            samples[name] = mean + std * np.sqrt(2) * _erfinv(2 * uniform_samples[:, i] - 1)

    # Add parameters that were skipped (zero uncertainty)
    if 'fok' not in samples:
        samples['fok'] = np.full(n, base_values.get('fok', 0))
    if 'slope_angle' not in samples:
        samples['slope_angle'] = np.full(n, base_values.get('slope_angle', 45))
    if 'foundation_depth' not in samples:
        samples['foundation_depth'] = np.full(n, base_values.get('foundation_depth', 3.5))
    if 'gravel_thickness' not in samples:
        samples['gravel_thickness'] = np.full(n, base_values.get('gravel_thickness', 0.5))
    if 'dem_noise' not in samples:
        samples['dem_noise'] = np.zeros(n)
    if 'boom_slope_noise' not in samples:
        samples['boom_slope_noise'] = np.zeros(n)
    if 'rotor_offset_noise' not in samples:
        samples['rotor_offset_noise'] = np.zeros(n)

    return samples


def _erfinv(x: np.ndarray) -> np.ndarray:
    """
    Approximate inverse error function (fallback when scipy not available).

    Uses Winitzki approximation.
    """
    a = 0.147
    sign = np.sign(x)
    x = np.abs(x)

    ln_term = np.log(1 - x * x)
    term1 = 2 / (np.pi * a) + ln_term / 2
    term2 = ln_term / a

    result = sign * np.sqrt(np.sqrt(term1 * term1 - term2) - term1)
    return result


def calculate_sobol_indices(
    samples: Dict[str, np.ndarray],
    output_values: np.ndarray,
    parameter_names: List[str]
) -> Dict[str, Tuple[float, float]]:
    """
    Calculate Sobol sensitivity indices using correlation-based approximation.

    For true Sobol indices, a special sampling design is needed.
    This function uses correlation-based sensitivity as an approximation.

    Args:
        samples: Dictionary of parameter samples
        output_values: Corresponding output values
        parameter_names: List of parameter names to analyze

    Returns:
        Dictionary mapping parameter names to (first_order, total) indices
    """
    indices = {}
    total_variance = np.var(output_values)

    if total_variance < 1e-10:
        # No variance in output - all sensitivities are zero
        return {name: (0.0, 0.0) for name in parameter_names}

    # Calculate correlation-based sensitivity for each parameter
    for name in parameter_names:
        if name not in samples:
            indices[name] = (0.0, 0.0)
            continue

        param_values = samples[name]

        if np.std(param_values) < 1e-10:
            # No variance in parameter
            indices[name] = (0.0, 0.0)
            continue

        # Pearson correlation as sensitivity measure
        correlation = np.corrcoef(param_values, output_values)[0, 1]
        if np.isnan(correlation):
            correlation = 0.0

        # Squared correlation approximates first-order Sobol index
        # for linear relationships
        first_order = correlation ** 2

        # For total index, we'd need a more sophisticated method
        # Use first_order as approximation
        total = first_order

        indices[name] = (first_order, total)

    # Normalize to sum to approximately 1
    total_sensitivity = sum(idx[0] for idx in indices.values())
    if total_sensitivity > 1e-10:
        indices = {
            name: (fo / total_sensitivity, to / total_sensitivity)
            for name, (fo, to) in indices.items()
        }

    return indices
