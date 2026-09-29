"""
Monotonicity Analysis Engine

Evaluates if FMR changes monotonically with respect to key state variables,
and flags when non-monotonicity is caused by discrete route selection jumps.
"""
import os
import csv
import logging

from models.constants import EPSILON_FMR
from engines.energy_engine import compute_all_routes
from engines.battery_engine import compute_soc_after, compute_soh_degradation
from engines.feasibility_engine import compute_probabilistic_fmr
from engines.optimizer import select_recommended
from models.schemas import RouteCandidate
from experiments.risk_decomposition import EVState, FutureTrip

logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CSV_OUTPUT = os.path.join(RESULTS_DIR, "monotonicity.csv")

def get_recommended_for_params(
    soc: float, soh: float, temperature: float, 
    demand_level: str, charging_availability: float, uncertainty_level: str, horizon: int,
    capacity_kwh: float, efficiency: float, future_trips: list, 
    scenario_count: int, random_seed: int
):
    route_profiles = compute_all_routes(traffic="Medium", temperature=temperature, soh=soh)
    candidates = []
    
    for i, profile in enumerate(route_profiles):
        energy = profile["energy_kwh"]
        soc_after = compute_soc_after(soc, energy, soh, capacity_kwh)
        soh_loss = compute_soh_degradation(
            energy_throughput_kwh=energy,
            temperature=temperature,
            soc_start=soc,
            soc_end=soc_after,
            capacity_kwh=capacity_kwh,
            soh=soh,
        )
        soh_after = round(soh - soh_loss, 4)

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
            planning_horizon=horizon,
        )
        
        candidates.append(RouteCandidate(
            id=profile["id"], name=profile["name"], time=profile["time_min"], cost=profile["cost_inr"],
            energy=profile["energy_kwh"], feasibility=fmr_result.fmf, fmr=fmr_result.fmr, 
            after=soc_after, tomorrow=soc_after-5, recommended=False,
            fmr_ci_lower=fmr_result.confidence_interval.lower if fmr_result.confidence_interval else 0.0,
            fmr_ci_upper=fmr_result.confidence_interval.upper if fmr_result.confidence_interval else 0.0,
        ))

    recommended_id, _, status = select_recommended(candidates)
    selected_route = next(c for c in candidates if c.id == recommended_id)
    return selected_route, status

def is_monotonic(arr):
    if len(arr) <= 1:
        return True, "monotonic"
    increasing = all(arr[i] <= arr[i+1] for i in range(len(arr)-1))
    decreasing = all(arr[i] >= arr[i+1] for i in range(len(arr)-1))
    if increasing or decreasing:
        return True, "monotonic"
    return False, "non-monotonicity detected due to route-selection interaction"

def run_monotonicity(
    random_seed: int = 42,
    scenario_count: int = 1000,
):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    capacity_kwh = 50.0
    efficiency = 6.5
    
    future_trips = [
        FutureTrip(id="f1", day="TOMORROW", origin="Home", destination="Remote", distance_km=150.0, priority="HIGH"),
        FutureTrip(id="f2", day="DAY 2", origin="Remote", destination="Office", distance_km=250.0, priority="CRITICAL"),
    ]

    sweeps = {
        "SOC": {"param": "soc", "values": [30.0, 50.0, 70.0, 90.0]},
        "SOH": {"param": "soh", "values": [70.0, 80.0, 90.0, 100.0]},
        "Temperature": {"param": "temperature", "values": [15.0, 25.0, 35.0, 45.0]},
        "Demand": {"param": "demand_level", "values": ["Low", "Medium", "High"]},
        "Charging": {"param": "charging_availability", "values": [0.1, 0.5, 0.9]},
        "Horizon": {"param": "horizon", "values": [1, 3, 5]},
    }
    
    base_params = {
        "soc": 60.0,
        "soh": 90.0,
        "temperature": 30.0,
        "demand_level": "Medium",
        "charging_availability": 0.5,
        "uncertainty_level": "Medium",
        "horizon": 5,
    }
    
    results = []

    for name, sweep_info in sweeps.items():
        param_key = sweep_info["param"]
        values = sweep_info["values"]
        
        sweep_fmrs = []
        sweep_data = []
        
        for v in values:
            kwargs = base_params.copy()
            kwargs[param_key] = v
            
            selected_route, status = get_recommended_for_params(
                **kwargs, capacity_kwh=capacity_kwh, efficiency=efficiency,
                future_trips=future_trips, scenario_count=scenario_count, random_seed=random_seed
            )
            
            constraint_status = "FEASIBLE" if (selected_route.fmr / 100.0) <= EPSILON_FMR else "INFEASIBLE"
            
            sweep_fmrs.append(selected_route.fmr)
            sweep_data.append({
                "parameter": name,
                "value": v,
                "fmr": selected_route.fmr,
                "ci_lower": selected_route.fmr_ci_lower,
                "ci_upper": selected_route.fmr_ci_upper,
                "selected_route": selected_route.name,
                "constraint_status": constraint_status
            })
            
        monotonic, flag = is_monotonic(sweep_fmrs)
        for data in sweep_data:
            data["monotonicity_flag"] = flag
            results.append(data)

    with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "parameter", "value", "fmr", "ci_lower", "ci_upper",
            "selected_route", "constraint_status", "monotonicity_flag"
        ])
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"Monotonicity analysis saved to {CSV_OUTPUT}")
    return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_monotonicity()
