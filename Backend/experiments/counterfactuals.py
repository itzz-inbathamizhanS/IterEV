"""
Counterfactual Decision Analysis

Evaluates controlled interventions on the selected route to determine which
controllable state variable most changes future mobility risk.
"""
import os
import csv
import logging
from copy import deepcopy

from models.schemas import RouteCandidate
from models.constants import EPSILON_FMR
from engines.energy_engine import compute_all_routes
from engines.battery_engine import compute_soc_after, compute_soh_degradation
from engines.feasibility_engine import compute_probabilistic_fmr
from engines.optimizer import select_recommended

from experiments.risk_decomposition import EVState, FutureTrip

logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CSV_OUTPUT = os.path.join(RESULTS_DIR, "counterfactuals.csv")

def get_fmr_for_route_with_intervention(
    profile, base_soc, base_soh, temperature, future_trips, capacity_kwh, efficiency,
    scenario_count, random_seed, planning_horizon,
    soc_modifier=0.0, soh_modifier=0.0,
    charging_availability=0.5, uncertainty_level="Medium", demand_level="Medium"
):
    start_soc = min(100.0, base_soc + soc_modifier)
    start_soh = min(100.0, base_soh + soh_modifier)

    energy = profile["energy_kwh"]
    soc_after = compute_soc_after(start_soc, energy, start_soh, capacity_kwh)
    soh_loss = compute_soh_degradation(
        energy_throughput_kwh=energy,
        temperature=temperature,
        soc_start=start_soc,
        soc_end=soc_after,
        capacity_kwh=capacity_kwh,
        soh=start_soh,
    )
    soh_after = round(start_soh - soh_loss, 4)

    fmr_result = compute_probabilistic_fmr(
        soc_after=soc_after,
        soh=soh_after,
        future_trips=future_trips,
        capacity_kwh=capacity_kwh,
        efficiency_km_kwh=efficiency,
        scenario_count=scenario_count,
        random_seed=random_seed,
        uncertainty_level=uncertainty_level,
        demand_level=demand_level,
        charging_availability=charging_availability,
        temperature=temperature,
        planning_horizon=planning_horizon,
    )
    return fmr_result.fmr


def run_counterfactuals(
    base_soc: float = 60.0,
    base_soh: float = 90.0,
    temperature: float = 30.0,
    random_seed: int = 42,
    scenario_count: int = 5000,
    horizon: int = 5,
):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    capacity_kwh = 50.0
    efficiency = 6.5
    
    future_trips = [
        FutureTrip(id="f1", day="TOMORROW", origin="A", destination="B", distance_km=180.0, priority="HIGH"),
        FutureTrip(id="f2", day="DAY 3", origin="B", destination="C", distance_km=220.0, priority="CRITICAL"),
    ]

    route_profiles = compute_all_routes(traffic="Medium", temperature=temperature, soh=base_soh)
    
    # 1. Run Baseline to find selected route
    candidates = []
    for i, profile in enumerate(route_profiles):
        fmr = get_fmr_for_route_with_intervention(
            profile, base_soc, base_soh, temperature, future_trips, capacity_kwh, efficiency,
            scenario_count, random_seed, horizon,
            charging_availability=0.5, uncertainty_level="Medium", demand_level="Medium"
        )
        candidates.append(RouteCandidate(
            id=profile["id"], name=profile["name"], time=profile["time_min"], cost=profile["cost_inr"],
            energy=profile["energy_kwh"], feasibility=100-fmr, fmr=fmr, after=0, tomorrow=0, recommended=False
        ))

    recommended_id, _, status = select_recommended(candidates)
    selected_route = next(c for c in candidates if c.id == recommended_id)
    selected_profile = next(p for p in route_profiles if p["id"] == recommended_id)
    baseline_fmr = selected_route.fmr

    # Interventions definition
    interventions = [
        ("BASE", {}),
        ("+10% initial SOC", {"soc_modifier": 10.0}),
        ("+20% initial SOC", {"soc_modifier": 20.0}),
        ("+5 SOH", {"soh_modifier": 5.0}),
        ("+10 SOH", {"soh_modifier": 10.0}),
        ("Guaranteed charging", {"charging_availability": 1.0}),
        ("Restricted charging", {"charging_availability": 0.1}),
        ("Low uncertainty", {"uncertainty_level": "Low"}),
        ("High uncertainty", {"uncertainty_level": "High"}),
        ("Reduced future demand", {"demand_level": "Low"}),
    ]

    results = []
    for name, params in interventions:
        kwargs = {
            "charging_availability": 0.5,
            "uncertainty_level": "Medium",
            "demand_level": "Medium",
        }
        kwargs.update(params)

        cf_fmr = get_fmr_for_route_with_intervention(
            selected_profile, base_soc, base_soh, temperature, future_trips, capacity_kwh, efficiency,
            scenario_count, random_seed, horizon, **kwargs
        )

        delta_fmr = cf_fmr - baseline_fmr
        relative_change = (delta_fmr / baseline_fmr * 100.0) if baseline_fmr > 0 else 0.0
        
        constraint_status = "FEASIBLE" if (cf_fmr / 100.0) <= EPSILON_FMR else "INFEASIBLE"

        results.append({
            "intervention": name,
            "baseline_fmr": round(baseline_fmr, 2),
            "counterfactual_fmr": round(cf_fmr, 2),
            "delta_fmr": round(delta_fmr, 2),
            "relative_change": f"{round(relative_change, 1)}%",
            "selected_route": selected_route.name,
            "constraint_status": constraint_status
        })

    with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "intervention", "baseline_fmr", "counterfactual_fmr", "delta_fmr",
            "relative_change", "selected_route", "constraint_status"
        ])
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"Counterfactuals saved to {CSV_OUTPUT}")
    return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_counterfactuals()
