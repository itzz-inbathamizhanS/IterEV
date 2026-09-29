"""
Charging Engine — Models charging as an explicit state transition.

Research reference: §15 — Charging model for route + charging actions.

Represents charging as an actual action/state transition with:
  - Charger availability (probabilistic)
  - Charger power and duration
  - Charging energy and cost
  - Charging efficiency losses
  - SOC transition from charging

This engine does NOT simulate real-time charging curves (CC/CV profiles).
It uses a simplified energy-balance model appropriate for planning-horizon
decisions (minutes to hours, not seconds).
"""

from models.constants import (
    DEFAULT_CHARGER_POWER_KW,
    CHARGING_EFFICIENCY,
    DEFAULT_CHARGING_COST_PER_KWH,
    MAX_CHARGING_SOC,
    NOMINAL_CAPACITY_KWH,
)


def compute_charging_energy(
    soc_before: float,
    soc_target: float,
    soh: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    charging_efficiency: float = CHARGING_EFFICIENCY,
) -> float:
    """
    Compute energy required from the grid to charge from soc_before to soc_target.

    Args:
        soc_before: SOC before charging (%)
        soc_target: Target SOC (%), capped at MAX_CHARGING_SOC
        soh: Battery State of Health (%)
        capacity_kwh: Nominal battery capacity (kWh)
        charging_efficiency: Wall-to-battery efficiency (0-1)

    Returns:
        Grid energy required (kWh).
    """
    soc_target = min(soc_target, MAX_CHARGING_SOC)
    if soc_target <= soc_before:
        return 0.0

    usable_kwh = capacity_kwh * (soh / 100.0)
    delta_soc = (soc_target - soc_before) / 100.0
    battery_energy = usable_kwh * delta_soc

    # Grid energy accounts for charging losses
    grid_energy = battery_energy / max(charging_efficiency, 0.01)
    return round(grid_energy, 2)


def compute_charging_duration(
    energy_kwh: float,
    charger_power_kw: float = DEFAULT_CHARGER_POWER_KW,
) -> float:
    """
    Estimate charging duration.

    Simple model: duration = energy / power.
    Does not model CC/CV taper — suitable for planning-level estimates.

    Args:
        energy_kwh: Grid energy to deliver (kWh)
        charger_power_kw: Charger power rating (kW)

    Returns:
        Estimated charging time (minutes).
    """
    if charger_power_kw <= 0 or energy_kwh <= 0:
        return 0.0
    hours = energy_kwh / charger_power_kw
    return round(hours * 60.0, 1)


def compute_charging_cost(
    energy_kwh: float,
    cost_per_kwh: float = DEFAULT_CHARGING_COST_PER_KWH,
) -> float:
    """
    Compute monetary cost of charging.

    Args:
        energy_kwh: Grid energy consumed (kWh)
        cost_per_kwh: Price per kWh (INR)

    Returns:
        Charging cost (INR).
    """
    return round(energy_kwh * cost_per_kwh, 1)


def compute_soc_after_charging(
    soc_before: float,
    charging_duration_min: float,
    soh: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    charger_power_kw: float = DEFAULT_CHARGER_POWER_KW,
    charging_efficiency: float = CHARGING_EFFICIENCY,
) -> float:
    """
    Compute SOC after a fixed-duration charging session.

    Used in future-state simulation when charging opportunity exists.

    Args:
        soc_before: SOC before charging (%)
        charging_duration_min: Available charging time (minutes)
        soh: Battery SOH (%)
        capacity_kwh: Nominal capacity (kWh)
        charger_power_kw: Charger power (kW)
        charging_efficiency: Efficiency (0-1)

    Returns:
        SOC after charging (%), capped at MAX_CHARGING_SOC.
    """
    usable_kwh = capacity_kwh * (soh / 100.0)
    if usable_kwh <= 0:
        return soc_before

    hours = charging_duration_min / 60.0
    grid_energy = charger_power_kw * hours
    battery_energy = grid_energy * charging_efficiency
    delta_soc = (battery_energy / usable_kwh) * 100.0

    soc_after = min(MAX_CHARGING_SOC, soc_before + delta_soc)
    return round(soc_after, 1)

import numpy as np

def compute_soc_after_charging_vec(
    soc_before: np.ndarray,
    charging_duration_min: np.ndarray,
    soh: np.ndarray,
    charger_available: np.ndarray,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    charger_power_kw: float = DEFAULT_CHARGER_POWER_KW,
    charging_efficiency: float = CHARGING_EFFICIENCY,
) -> np.ndarray:
    """
    Vectorized SOC computation after charging for Monte Carlo simulation.
    Ensures charging cannot create energy from nowhere:
    - Only adds energy if charger_available is True
    - Time and power must be > 0
    - SOC cannot exceed MAX_CHARGING_SOC
    """
    if charger_power_kw <= 0:
        return soc_before.copy()
        
    usable_kwh = capacity_kwh * (soh / 100.0)
    
    # Grid energy based on power and time
    # Time must be positive
    valid_duration = np.maximum(0.0, charging_duration_min)
    hours = valid_duration / 60.0
    grid_energy = charger_power_kw * hours
    
    # Battery energy added
    battery_energy = grid_energy * charging_efficiency
    
    # Calculate SOC gain
    delta_soc = np.where(
        (usable_kwh > 0) & charger_available, 
        (battery_energy / np.maximum(usable_kwh, 0.01)) * 100.0, 
        0.0
    )
    
    # Add to current SOC and cap at MAX_CHARGING_SOC
    soc_after = np.minimum(MAX_CHARGING_SOC, soc_before + delta_soc)
    return soc_after

