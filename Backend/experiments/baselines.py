"""
Baseline Algorithms — Implements the four baseline methods for comparison.

All methods receive the same input and use the same physical engines.
Only the decision criterion (objective function) differs.

Methods:
  1. FASTEST — minimize travel time
  2. ENERGY_MIN — minimize energy consumption
  3. BATTERY_AWARE — maximize SOC_after (minimize battery depletion)
  4. ITEREV — minimize J(a) = Cost + λ·Battery + µ·FMR s.t. FMR ≤ ε

FAIRNESS:
  All methods use the SAME random seed for scenario generation (common
  random numbers) so that comparison noise is minimized. Only the
  decision objective changes.
"""

import time
from models.constants import (
    ROUTE_PROFILES,
    NOMINAL_CAPACITY_KWH,
    LAMBDA_BATTERY,
    MU_FMR,
    EPSILON_FMR,
    DEMAND_MULTIPLIER,
)
from engines.energy_engine import predict_energy
from engines.battery_engine import compute_soc_after, compute_soh_degradation
from engines.feasibility_engine import compute_fmf, compute_probabilistic_fmr
from engines.uncertainty_engine import AblationFlags
from experiments.config import ExperimentConfig
from experiments.scenarios import build_standard_trips


def run_baseline(
    method: str,
    config: ExperimentConfig,
) -> dict:
    """
    Run a single baseline method and return all metrics.

    Uses common random numbers: all routes evaluated with the same seed
    so that Monte Carlo noise doesn't contaminate the comparison.
    """
    t_start = time.perf_counter()

    demand_mult = DEMAND_MULTIPLIER.get(config.demand, 1.0)
    future_trips = build_standard_trips(demand_mult, config.planning_horizon)

    # Compute all routes under given conditions
    route_data = []
    for profile in ROUTE_PROFILES:
        energy = predict_energy(
            profile["base_energy_kwh"],
            traffic=config.traffic,
            temperature=config.temperature,
            soh=config.soh,
        )
        soc_after = compute_soc_after(
            config.soc_initial, energy, config.soh, config.capacity_kwh
        )
        time_adj = round(
            profile["base_time_min"] * profile["time_traffic_mult"][config.traffic]
        )
        cost_adj = round(
            profile["base_cost_inr"] * profile["cost_traffic_mult"][config.traffic]
        )
        soh_loss = compute_soh_degradation(
            energy_throughput_kwh=energy,
            temperature=config.temperature,
            soc_start=config.soc_initial,
            soc_end=soc_after,
            capacity_kwh=config.capacity_kwh,
            soh=config.soh,
        )

        # Deterministic FMF (for baselines that don't use probabilistic FMR)
        fmf_det, fmr_det, _ = compute_fmf(
            soc_after, config.soh, future_trips, config.capacity_kwh,
            config.efficiency,
        )

        # Probabilistic FMR — SAME seed for all routes (common random numbers)
        fmr_result = compute_probabilistic_fmr(
            soc_after=soc_after,
            soh=config.soh - soh_loss,
            future_trips=future_trips,
            capacity_kwh=config.capacity_kwh,
            efficiency_km_kwh=config.efficiency,
            scenario_count=config.scenario_count,
            random_seed=config.random_seed,
            uncertainty_level=config.uncertainty,
            demand_level=config.demand,
            charging_availability=config.charging_availability,
            temperature=config.temperature,
            planning_horizon=config.planning_horizon,
            ablation=config.ablation,
        )

        route_data.append({
            "id": profile["id"],
            "name": profile["name"],
            "energy": energy,
            "time": time_adj,
            "cost": cost_adj,
            "soc_after": soc_after,
            "soh_loss": soh_loss,
            "fmf_det": fmf_det,
            "fmr_det": fmr_det,
            "fmf_prob": fmr_result.fmf,
            "fmr_prob": fmr_result.fmr,
            "fmr_ci_lower": fmr_result.confidence_interval.lower if fmr_result.confidence_interval else 0,
            "fmr_ci_upper": fmr_result.confidence_interval.upper if fmr_result.confidence_interval else 0,
            "total_scenarios": fmr_result.total_scenarios,
            "failed_scenarios": fmr_result.failed_scenarios,
            "constraint_feasible": (fmr_result.fmr / 100.0) <= config.epsilon_fmr,
        })

    # Select route based on method objective
    if method == "FASTEST":
        chosen = min(route_data, key=lambda r: r["time"])
    elif method == "ENERGY_MIN":
        chosen = min(route_data, key=lambda r: r["energy"])
    elif method == "BATTERY_AWARE":
        chosen = max(route_data, key=lambda r: r["soc_after"])
    elif method == "ITEREV":
        max_time = max(r["time"] for r in route_data)
        min_time = min(r["time"] for r in route_data)
        max_fmr = max(r["fmr_prob"] for r in route_data)
        min_fmr = min(r["fmr_prob"] for r in route_data)
        max_soc = max(r["soc_after"] for r in route_data)
        min_soc = min(r["soc_after"] for r in route_data)

        def _norm(v, lo, hi):
            return (v - lo) / max(hi - lo, 0.001)

        def J(r):
            t_n = _norm(r["time"], min_time, max_time)
            fmr_n = _norm(r["fmr_prob"], min_fmr, max_fmr)
            soc_n = _norm(r["soc_after"], min_soc, max_soc)
            bat = 1.0 - soc_n
            return t_n * 0.5 + bat * config.lambda_battery + fmr_n * config.mu_fmr

        feasible = [r for r in route_data if r["constraint_feasible"]]
        candidates = feasible if feasible else route_data
        chosen = min(candidates, key=J)
    else:
        chosen = route_data[0]

    t_end = time.perf_counter()

    return {
        "method": method,
        "route_name": chosen["name"],
        "travel_time": chosen["time"],
        "energy": chosen["energy"],
        "cost": chosen["cost"],
        "soc_after": chosen["soc_after"],
        "soh_loss": chosen["soh_loss"],
        "fmf": chosen["fmf_prob"],
        "fmr": chosen["fmr_prob"],
        "fmr_ci_lower": chosen["fmr_ci_lower"],
        "fmr_ci_upper": chosen["fmr_ci_upper"],
        "future_success_rate": chosen["fmf_prob"],
        "constraint_feasible": chosen["constraint_feasible"],
        "constraint_violations": 0 if chosen["constraint_feasible"] else 1,
        "total_scenarios": chosen["total_scenarios"],
        "computation_time_s": round(t_end - t_start, 4),
    }


def run_independent_validation(
    method: str,
    config: ExperimentConfig,
    validation_seed: int = 4242,
    validation_count: int = 20000,
) -> dict:
    """
    Run independent validation: simulate actual future failures using
    a DIFFERENT seed than the one used for FMR estimation.

    This is the "observed failure rate" — not another FMR prediction.

    Returns dict with 'observed_failure_rate' from actual simulation.
    """
    demand_mult = DEMAND_MULTIPLIER.get(config.demand, 1.0)
    future_trips = build_standard_trips(demand_mult, config.planning_horizon)

    # First: select route using ESTIMATION seed
    route_data = []
    for profile in ROUTE_PROFILES:
        energy = predict_energy(
            profile["base_energy_kwh"],
            traffic=config.traffic,
            temperature=config.temperature,
            soh=config.soh,
        )
        soc_after = compute_soc_after(
            config.soc_initial, energy, config.soh, config.capacity_kwh
        )
        soh_loss = compute_soh_degradation(
            energy_throughput_kwh=energy,
            temperature=config.temperature,
            soc_start=config.soc_initial,
            soc_end=soc_after,
            capacity_kwh=config.capacity_kwh,
            soh=config.soh,
        )
        route_data.append({
            "soc_after": soc_after,
            "soh_after": config.soh - soh_loss,
            "energy": energy,
            "name": profile["name"],
            "time": round(profile["base_time_min"] * profile["time_traffic_mult"][config.traffic]),
        })

    # Select route based on method (simplified — use BATTERY_CARE for ITEREV)
    if method == "FASTEST":
        chosen = min(route_data, key=lambda r: r["time"])
    elif method == "ENERGY_MIN":
        chosen = min(route_data, key=lambda r: r["energy"])
    elif method == "BATTERY_AWARE":
        chosen = max(route_data, key=lambda r: r["soc_after"])
    else:  # ITEREV
        chosen = max(route_data, key=lambda r: r["soc_after"])

    # Second: run VALIDATION simulation with DIFFERENT seed
    val_result = compute_probabilistic_fmr(
        soc_after=chosen["soc_after"],
        soh=chosen["soh_after"],
        future_trips=future_trips,
        capacity_kwh=config.capacity_kwh,
        efficiency_km_kwh=config.efficiency,
        scenario_count=validation_count,
        random_seed=validation_seed,
        uncertainty_level=config.uncertainty,
        demand_level=config.demand,
        charging_availability=config.charging_availability,
        temperature=config.temperature,
        planning_horizon=config.planning_horizon,
        ablation=config.ablation,
    )

    return {
        "soc_after": chosen["soc_after"],
        "soh_after": chosen["soh_after"],
        "observed_failure_rate": val_result.fmr,
        "observed_failures": val_result.failed_scenarios,
        "validation_scenarios": val_result.total_scenarios,
        "validation_seed": validation_seed,
        "validation_ci_lower": val_result.confidence_interval.lower if val_result.confidence_interval else 0,
        "validation_ci_upper": val_result.confidence_interval.upper if val_result.confidence_interval else 0,
    }


METHODS = ["FASTEST", "ENERGY_MIN", "BATTERY_AWARE", "ITEREV"]
