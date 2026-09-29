"""
Simulation API — POST /api/simulation/run with research-grade baseline comparisons.

Implements the method comparison:
  FASTEST        → minimize travel time only
  ENERGY AWARE   → minimize energy consumption
  BATTERY AWARE  → minimize battery degradation (maximize SOC_after)
  PROPOSED       → minimize J(a) = CurrentCost + λ·Battery + µ·FMR

Each method uses the SAME energy, battery, and feasibility engines —
only the decision objective differs. This ensures a fair comparison
(same physical model, different decision criteria).

ALL simulation inputs now affect backend computation:
  horizon, soh, temperature, traffic, demand, charging, uncertainty,
  scenario_count, random_seed, charging_availability, soc_initial.

Research reference: §21 Experimental Design — Baselines section.
"""

from fastapi import APIRouter
from models.schemas import (
    SimulationInput,
    SimulationOutput,
    SimulationResult,
    MethodComparisonRow,
    FutureTrip,
)
from models.constants import (
    ROUTE_PROFILES,
    NOMINAL_CAPACITY_KWH,
    DEMAND_MULTIPLIER,
    LAMBDA_BATTERY,
    MU_FMR,
    EPSILON_FMR,
)
from engines.energy_engine import predict_energy
from engines.battery_engine import compute_soc_after, compute_soh_degradation
from engines.feasibility_engine import compute_fmf, compute_probabilistic_fmr

router = APIRouter(prefix="/api/simulation", tags=["simulation"])


def _build_future_trips(
    horizon: int,
    demand: str,
) -> list[FutureTrip]:
    """
    Build future trips for simulation based on demand level and horizon.

    Demand level scales trip distances:
      Low: shorter trips
      Medium: standard trips (Chennai 500km, Bangalore 330km)
      High: longer trips
    """
    demand_mult = DEMAND_MULTIPLIER.get(demand, 1.0)

    # Base future trips: long-distance Chennai + medium-distance Bangalore
    base_trips = [
        {"day": "TOMORROW", "dest": "Chennai", "dist": 500.0, "priority": "CRITICAL"},
        {"day": f"DAY {min(horizon, 5)}", "dest": "Bangalore", "dist": 330.0, "priority": "HIGH"},
    ]

    # Add local trips for longer horizons
    if horizon > 3:
        base_trips.append(
            {"day": "DAY 3", "dest": "Local Mobility", "dist": 60.0, "priority": "NORMAL"}
        )
    if horizon > 7:
        base_trips.append(
            {"day": "DAY 7", "dest": "Regional", "dist": 150.0, "priority": "HIGH"}
        )

    trips = []
    for i, t in enumerate(base_trips):
        trips.append(FutureTrip(
            id=f"sim_{i}",
            day=t["day"],
            origin="Simulation",
            destination=t["dest"],
            distance_km=round(t["dist"] * demand_mult, 1),
            priority=t["priority"],
        ))

    return trips


def _run_method(
    method: str,
    sim_input: SimulationInput,
    future_trips: list[FutureTrip],
) -> tuple[MethodComparisonRow, float]:
    """
    Run one optimization method and return its result row + SOC_after.

    Each method selects a route from ROUTE_PROFILES based on its own objective.
    All methods use the same physical engines — only the selection criterion differs.
    """
    capacity_kwh = NOMINAL_CAPACITY_KWH
    soc_initial = sim_input.soc_initial

    # Compute energy and battery consequence for all routes
    route_results = []
    for profile in ROUTE_PROFILES:
        energy = predict_energy(
            profile["base_energy_kwh"],
            traffic=sim_input.traffic,
            temperature=sim_input.temperature,
            soh=sim_input.soh,
        )
        soc_after = compute_soc_after(soc_initial, energy, sim_input.soh, capacity_kwh)
        time_adj = round(profile["base_time_min"] * profile["time_traffic_mult"][sim_input.traffic])
        cost_adj = round(profile["base_cost_inr"] * profile["cost_traffic_mult"][sim_input.traffic])

        # SOH degradation
        soh_loss = compute_soh_degradation(
            energy_throughput_kwh=energy,
            temperature=sim_input.temperature,
            soc_start=soc_initial,
            soc_end=soc_after,
            capacity_kwh=capacity_kwh,
            soh=sim_input.soh,
        )

        # Probabilistic FMR (all methods get the same FMR info for fair comparison)
        fmr_result = compute_probabilistic_fmr(
            soc_after=soc_after,
            soh=sim_input.soh - soh_loss,
            future_trips=future_trips,
            capacity_kwh=capacity_kwh,
            scenario_count=min(sim_input.scenario_count, 2000),  # Cap for speed in simulation
            random_seed=sim_input.random_seed,
            uncertainty_level=sim_input.uncertainty,
            demand_level=sim_input.demand,
            charging_availability=sim_input.charging_availability,
            temperature=sim_input.temperature,
            planning_horizon=sim_input.horizon,
        )

        route_results.append({
            "profile": profile,
            "energy": energy,
            "soc_after": soc_after,
            "time": time_adj,
            "cost": cost_adj,
            "fmf": fmr_result.fmf,
            "fmr": fmr_result.fmr,
            "soh_loss": soh_loss,
            "success_rate": fmr_result.fmf,
            "constraint_violation": 1 if (fmr_result.fmr / 100.0) > EPSILON_FMR else 0,
        })

    # Select route based on method objective
    if method == "FASTEST":
        chosen = min(route_results, key=lambda r: r["time"])
    elif method == "ENERGY AWARE":
        chosen = min(route_results, key=lambda r: r["energy"])
    elif method == "BATTERY AWARE":
        chosen = max(route_results, key=lambda r: r["soc_after"])
    else:  # PROPOSED — full J(a) optimizer
        max_time = max(r["time"] for r in route_results)
        min_time = min(r["time"] for r in route_results)
        max_fmr = max(r["fmr"] for r in route_results)
        min_fmr = min(r["fmr"] for r in route_results)
        max_soc = max(r["soc_after"] for r in route_results)
        min_soc = min(r["soc_after"] for r in route_results)

        def J(r: dict) -> float:
            t_range = max(max_time - min_time, 1)
            fmr_range = max(max_fmr - min_fmr, 0.001)
            soc_range = max(max_soc - min_soc, 0.001)
            t_norm = (r["time"] - min_time) / t_range
            fmr_norm = (r["fmr"] - min_fmr) / fmr_range
            soc_norm = (r["soc_after"] - min_soc) / soc_range
            battery_consequence = 1.0 - soc_norm
            return t_norm * 0.5 + battery_consequence * LAMBDA_BATTERY + fmr_norm * MU_FMR

        # Filter feasible routes first
        feasible = [r for r in route_results if (r["fmr"] / 100.0) <= EPSILON_FMR]
        candidates = feasible if feasible else route_results
        chosen = min(candidates, key=J)

    return MethodComparisonRow(
        method=method,
        travelTime=chosen["time"],
        energy=chosen["energy"],
        feasibility=chosen["fmf"],
        risk=chosen["fmr"],
        soh_loss=round(chosen["soh_loss"] * 100, 4),  # Convert to basis points
        future_success_rate=chosen["success_rate"],
        constraint_violations=chosen["constraint_violation"],
    ), chosen["soc_after"]


@router.post("/run", response_model=SimulationResult)
async def run_simulation(sim_input: SimulationInput) -> SimulationResult:
    """
    Run the full simulation with all 4 methods and return comparison results.

    ALL input parameters now affect the computation:
      - horizon: determines future trip schedule
      - soh: battery health affects energy and degradation
      - temperature: affects energy consumption
      - traffic: affects energy and time
      - demand: scales future trip distances
      - charging: affects charging availability
      - uncertainty: controls distribution widths
      - scenario_count: number of Monte Carlo scenarios
      - random_seed: for reproducibility
      - charging_availability: P(charger available)
      - soc_initial: starting SOC

    This produces a FAIR, COMPUTED comparison — all methods receive the same
    scenario inputs and use the same physical engines.
    """
    # Adjust charging availability based on charging input
    if sim_input.charging == "Restricted":
        sim_input.charging_availability = min(sim_input.charging_availability, 0.5)

    # Build future trips based on horizon and demand
    future_trips = _build_future_trips(sim_input.horizon, sim_input.demand)

    methods = ["FASTEST", "ENERGY AWARE", "BATTERY AWARE", "PROPOSED"]
    comparison = []
    proposed_row = None
    proposed_soc = sim_input.soc_initial

    for method in methods:
        row, soc_after = _run_method(method, sim_input, future_trips)
        comparison.append(row)
        if method == "PROPOSED":
            proposed_row = row
            proposed_soc = soc_after

    if proposed_row is None:
        proposed_row = comparison[-1]

    # Compute FMR confidence interval for the proposed method
    proposed_fmr_result = compute_probabilistic_fmr(
        soc_after=proposed_soc,
        soh=sim_input.soh,
        future_trips=future_trips,
        scenario_count=sim_input.scenario_count,
        random_seed=sim_input.random_seed,
        uncertainty_level=sim_input.uncertainty,
        demand_level=sim_input.demand,
        charging_availability=sim_input.charging_availability,
        temperature=sim_input.temperature,
        planning_horizon=sim_input.horizon,
    )

    ci = proposed_fmr_result.confidence_interval

    primary = SimulationOutput(
        feasibility=proposed_row.feasibility,
        risk=proposed_row.risk,
        energy=proposed_row.energy,
        travelTime=proposed_row.travelTime,
        riskRange=round((ci.upper - ci.lower) if ci else 0.0, 2),
        fmr_ci_lower=ci.lower if ci else 0.0,
        fmr_ci_upper=ci.upper if ci else 0.0,
        total_scenarios=proposed_fmr_result.total_scenarios,
        soh_loss=proposed_row.soh_loss,
    )

    return SimulationResult(
        primary=primary,
        comparison=comparison,
        is_computed=True,
        random_seed=sim_input.random_seed,
        scenario_count=sim_input.scenario_count,
    )
