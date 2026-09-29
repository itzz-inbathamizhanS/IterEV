"""
Uncertainty Engine — Scenario sampling for probabilistic FMR estimation.

This engine generates N future scenarios by sampling uncertain variables:
  - Energy consumption uncertainty (multiplicative noise)
  - Temperature variability
  - Traffic conditions (categorical sampling)
  - Future trip demand scaling
  - Charging station availability (Bernoulli)
  - Battery degradation variability

The engine uses NumPy for vectorized sampling and supports reproducible
results via configurable random seeds.

Research reference:
  §18 — "FMR(a) = P[I_future(a, ω) = 0]"
  ω represents the uncertain environment variables sampled here.
"""

import numpy as np
from models.constants import (
    ENERGY_UNCERTAINTY_SIGMA,
    TEMPERATURE_VARIABILITY_STD,
    TRAFFIC_DISTRIBUTIONS,
    TRAFFIC_FACTORS,
    DEMAND_MULTIPLIER,
    DEFAULT_CHARGING_AVAILABILITY,
    DEFAULT_SCENARIO_COUNT,
    DEFAULT_RANDOM_SEED,
)


class ScenarioSet:
    """
    A set of N sampled future scenarios for Monte Carlo FMR estimation.

    Each attribute is a numpy array of shape (N,) or (N, horizon_days)
    containing sampled values for each scenario.
    """

    def __init__(
        self,
        energy_multipliers: np.ndarray,
        temperature_offsets: np.ndarray,
        traffic_levels: np.ndarray,
        traffic_factors: np.ndarray,
        demand_multipliers: np.ndarray,
        charger_available: np.ndarray,
        degradation_noise: np.ndarray,
        seed: int,
        n_scenarios: int,
    ):
        self.energy_multipliers = energy_multipliers
        self.temperature_offsets = temperature_offsets
        self.traffic_levels = traffic_levels
        self.traffic_factors = traffic_factors
        self.demand_multipliers = demand_multipliers
        self.charger_available = charger_available
        self.degradation_noise = degradation_noise
        self.seed = seed
        self.n_scenarios = n_scenarios


def generate_scenarios(
    n_scenarios: int = DEFAULT_SCENARIO_COUNT,
    horizon_days: int = 5,
    uncertainty_level: str = "Medium",
    demand_level: str = "Medium",
    charging_availability: float = DEFAULT_CHARGING_AVAILABILITY,
    base_temperature: float = 29.0,
    random_seed: int = DEFAULT_RANDOM_SEED,
) -> ScenarioSet:
    """
    Generate N future scenarios by sampling uncertain variables.

    Args:
        n_scenarios: Number of Monte Carlo scenarios
        horizon_days: Number of future days to simulate
        uncertainty_level: "Low" | "Medium" | "High" — controls distribution widths
        demand_level: "Low" | "Medium" | "High" | "Very High" — scales trip distances
        charging_availability: P(charger available) for Bernoulli sampling
        base_temperature: Mean temperature for sampling
        random_seed: For reproducibility

    Returns:
        ScenarioSet with all sampled variables.
    """
    rng = np.random.default_rng(random_seed)

    # 1. Energy uncertainty: multiplicative noise ~ Normal(1.0, sigma)
    sigma = ENERGY_UNCERTAINTY_SIGMA.get(uncertainty_level, 0.08)
    energy_multipliers = rng.normal(1.0, sigma, size=(n_scenarios, horizon_days))
    # Clip to physically reasonable range [0.7, 1.5]
    energy_multipliers = np.clip(energy_multipliers, 0.7, 1.5)

    # 2. Temperature variability: offset ~ Normal(0, std)
    temp_std = TEMPERATURE_VARIABILITY_STD.get(uncertainty_level, 3.0)
    temperature_offsets = rng.normal(0.0, temp_std, size=(n_scenarios, horizon_days))

    # 3. Traffic: categorical sampling from distribution
    traffic_dist = TRAFFIC_DISTRIBUTIONS.get(uncertainty_level, TRAFFIC_DISTRIBUTIONS["Medium"])
    traffic_labels = list(traffic_dist.keys())
    traffic_probs = np.array([traffic_dist[t] for t in traffic_labels])
    traffic_indices = rng.choice(len(traffic_labels), size=(n_scenarios, horizon_days), p=traffic_probs)
    traffic_levels = np.array(traffic_labels)[traffic_indices]

    # Pre-compute traffic factors for vectorized computation
    factor_map = {label: TRAFFIC_FACTORS[label] for label in traffic_labels}
    traffic_factors_arr = np.vectorize(factor_map.get)(traffic_levels).astype(float)

    # 4. Demand multiplier (applied to trip distances)
    base_demand_mult = DEMAND_MULTIPLIER.get(demand_level, 1.0)
    # Add per-scenario variability: ±10% around the base
    demand_noise = rng.normal(1.0, 0.10, size=(n_scenarios,))
    demand_multipliers = np.clip(base_demand_mult * demand_noise, 0.5, 2.5)

    # 5. Charging availability: Bernoulli per day per scenario
    charger_available = rng.random(size=(n_scenarios, horizon_days)) < charging_availability

    # 6. Degradation noise: small multiplicative variation
    degradation_noise = rng.normal(1.0, 0.05, size=(n_scenarios,))
    degradation_noise = np.clip(degradation_noise, 0.8, 1.2)

    return ScenarioSet(
        energy_multipliers=energy_multipliers,
        temperature_offsets=temperature_offsets,
        traffic_levels=traffic_levels,
        traffic_factors=traffic_factors_arr,
        demand_multipliers=demand_multipliers,
        charger_available=charger_available,
        degradation_noise=degradation_noise,
        seed=random_seed,
        n_scenarios=n_scenarios,
    )
