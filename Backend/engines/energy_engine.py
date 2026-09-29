"""
Energy Engine — Research Module 2 (Consequence Engine, energy prediction component).

Research reference: Section 12 §2 — "Consequence engine: predicts energy use and
battery-state change for each candidate route, charging action or vehicle assignment."

Formula basis:
  E(route) = E_base × f_traffic × f_temperature × f_soh

Where:
  E_base      = base energy from route profile (calibrated at standard conditions)
  f_traffic   = traffic multiplier (free-flow → congested: 0.88 → 1.20)
  f_temperature = temperature multiplier (Arrhenius-inspired Li-ion efficiency curve)
  f_soh       = SOH degradation factor (degraded battery has lower efficiency)

Note: the base energy profiles for Phase 1 (Coimbatore→Ooty) are calibrated at:
  SOH=94%, temperature=25°C, traffic=Medium.
"""

from models.constants import (
    TRAFFIC_FACTORS,
    TEMP_SENSITIVITY_PER_DEGREE,
    BASELINE_TEMP_C,
    BASELINE_SOH,
    SOH_ENERGY_FACTOR_PER_POINT,
    ROUTE_PROFILES,
)


def predict_energy(
    base_energy_kwh: float,
    traffic: str,
    temperature: float,
    soh: float,
) -> float:
    """
    Predict route energy consumption under given conditions.

    Args:
        base_energy_kwh: Calibrated base consumption at standard conditions (kWh)
        traffic: "Low" | "Medium" | "High"
        temperature: Battery temperature (°C)
        soh: State of Health (%)

    Returns:
        Predicted energy consumption (kWh), rounded to 1 decimal place.
    """
    # Traffic multiplier — stop-go driving increases energy consumption significantly
    f_traffic = TRAFFIC_FACTORS[traffic]

    # Temperature multiplier — both hot and cold reduce efficiency
    # Li-ion batteries degrade faster and have higher internal resistance outside 20-35°C
    temp_delta = abs(temperature - BASELINE_TEMP_C)
    f_temp = 1.0 + temp_delta * TEMP_SENSITIVITY_PER_DEGREE

    # SOH degradation factor — reduced chemical capacity means lower round-trip efficiency
    soh_deficit = max(0.0, BASELINE_SOH - soh)
    f_soh = 1.0 + soh_deficit * SOH_ENERGY_FACTOR_PER_POINT

    energy = base_energy_kwh * f_traffic * f_temp * f_soh
    return round(max(0.1, energy), 1)


def predict_travel_time(
    base_time_min: int,
    traffic: str,
    traffic_mult: dict[str, float],
) -> int:
    """
    Predict travel time adjusted for traffic conditions.

    Args:
        base_time_min: Base travel time at medium traffic (minutes)
        traffic: "Low" | "Medium" | "High"
        traffic_mult: Route-specific traffic time multipliers

    Returns:
        Adjusted travel time (minutes), rounded to nearest integer.
    """
    return round(base_time_min * traffic_mult[traffic])


def predict_cost(
    base_cost_inr: int,
    traffic: str,
    cost_mult: dict[str, float],
) -> int:
    """
    Predict trip cost (tolls + charging cost estimate) adjusted for traffic.
    Higher traffic → more charging needed → higher cost.

    Args:
        base_cost_inr: Base trip cost at medium traffic (INR)
        traffic: "Low" | "Medium" | "High"
        cost_mult: Route-specific traffic cost multipliers

    Returns:
        Adjusted cost (INR), rounded to nearest integer.
    """
    return round(base_cost_inr * cost_mult[traffic])


def compute_all_routes(traffic: str, temperature: float, soh: float) -> list[dict]:
    """
    Compute energy, time, and cost for all route profiles under given conditions.

    Args:
        traffic: Current traffic level
        temperature: Battery temperature (°C)
        soh: State of Health (%)

    Returns:
        List of route profile dicts with computed energy, time, cost fields added.
    """
    result = []
    for profile in ROUTE_PROFILES:
        computed = {
            **profile,
            "energy_kwh": predict_energy(
                profile["base_energy_kwh"], traffic, temperature, soh
            ),
            "time_min": predict_travel_time(
                profile["base_time_min"], traffic, profile["time_traffic_mult"]
            ),
            "cost_inr": predict_cost(
                profile["base_cost_inr"], traffic, profile["cost_traffic_mult"]
            ),
        }
        result.append(computed)
    return result
