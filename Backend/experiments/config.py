"""
Experiment Configuration — Centralized experiment parameter definitions.

All experiment configurations are defined here so that experiments
are reproducible and systematically controlled.
"""

from dataclasses import dataclass, field


@dataclass
class ExperimentConfig:
    """Configuration for a single experiment run."""
    name: str = "default"
    scenario_count: int = 5000
    random_seed: int = 42
    soc_initial: float = 78.0
    soh: float = 94.0
    temperature: float = 29.0
    traffic: str = "Medium"
    demand: str = "Medium"
    uncertainty: str = "Medium"
    charging_availability: float = 0.95
    planning_horizon: int = 5
    capacity_kwh: float = 80.0
    efficiency: float = 6.0
    lambda_battery: float = 0.30
    mu_fmr: float = 0.50
    epsilon_fmr: float = 0.10

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "scenario_count": self.scenario_count,
            "random_seed": self.random_seed,
            "soc_initial": self.soc_initial,
            "soh": self.soh,
            "temperature": self.temperature,
            "traffic": self.traffic,
            "demand": self.demand,
            "uncertainty": self.uncertainty,
            "charging_availability": self.charging_availability,
            "planning_horizon": self.planning_horizon,
            "capacity_kwh": self.capacity_kwh,
            "efficiency": self.efficiency,
            "lambda_battery": self.lambda_battery,
            "mu_fmr": self.mu_fmr,
            "epsilon_fmr": self.epsilon_fmr,
        }


# Standard experiment scenarios
DEFAULT_CONFIG = ExperimentConfig()

SOC_VALUES = [20, 30, 40, 50, 60, 70, 80, 90]
SOH_VALUES = [100, 95, 90, 85, 80, 75, 70]
TEMPERATURE_VALUES = [15, 20, 25, 30, 35, 40, 45]
DEMAND_LEVELS = ["Low", "Medium", "High", "Very High"]
CHARGING_AVAILABILITIES = [1.00, 0.90, 0.75, 0.50, 0.25]
PLANNING_HORIZONS = [1, 3, 5, 7, 14]
UNCERTAINTY_LEVELS = ["Low", "Medium", "High"]
MC_SAMPLE_SIZES = [100, 500, 1000, 5000, 10000]
