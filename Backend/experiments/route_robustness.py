"""
Route Robustness Analysis

For every candidate route, calculates FMR, confidence intervals, physical metrics,
and constraint margins to assess overall analytical robustness without enforcing a single ranking.
"""
import os
import csv
import logging

from models.constants import EPSILON_FMR
from engines.energy_engine import compute_all_routes
from engines.battery_engine import compute_soc_after, compute_soh_degradation
from engines.feasibility_engine import compute_probabilistic_fmr

from experiments.risk_decomposition import EVState, FutureTrip

logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CSV_OUTPUT = os.path.join(RESULTS_DIR, "route_robustness.csv")

def run_route_robustness(
    soc: float = 65.0,
    soh: float = 95.0,
    temperature: float = 30.0,
    random_seed: int = 42,
    scenario_count: int = 10000,
    horizon: int = 5,
):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    capacity_kwh = 50.0
    efficiency = 6.5
    
    future_trips = [
        FutureTrip(id="f1", day="TOMORROW", origin="Home", destination="Remote", distance_km=150.0, priority="HIGH"),
        FutureTrip(id="f2", day="DAY 2", origin="Remote", destination="Office", distance_km=250.0, priority="CRITICAL"),
        FutureTrip(id="f3", day="DAY 4", origin="Office", destination="Home", distance_km=50.0, priority="NORMAL"),
    ]

    route_profiles = compute_all_routes(traffic="Medium", temperature=temperature, soh=soh)
    
    results = []
    eps_percent = EPSILON_FMR * 100.0

    for profile in route_profiles:
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
            planning_horizon=horizon,
        )
        
        fmr = fmr_result.fmr
        ci = fmr_result.confidence_interval
        ci_lower = ci.lower if ci else 0.0
        ci_upper = ci.upper if ci else 0.0
        fmf = fmr_result.fmf
        
        risk_margin = eps_percent - fmr
        relative_risk_margin = risk_margin / eps_percent if eps_percent > 0 else 0.0
        
        # Point estimate constraint check
        if fmr > eps_percent:
            constraint_status = "INFEASIBLE"
        elif fmr > (eps_percent * 0.8):
            constraint_status = "NEAR CONSTRAINT"
        else:
            constraint_status = "FEASIBLE"
            
        results.append({
            "route_name": profile["name"],
            "fmr": fmr,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "fmf": fmf,
            "energy_kwh": energy,
            "time_min": profile["time_min"],
            "cost_inr": profile["cost_inr"],
            "soc_after": soc_after,
            "soh_after": soh_after,
            "risk_margin": round(risk_margin, 2),
            "relative_risk_margin": round(relative_risk_margin, 3),
            "constraint_status": constraint_status
        })

    with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "route_name", "fmr", "ci_lower", "ci_upper", "fmf", 
            "energy_kwh", "time_min", "cost_inr", "soc_after", "soh_after",
            "risk_margin", "relative_risk_margin", "constraint_status"
        ])
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"Route robustness saved to {CSV_OUTPUT}")
    return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_route_robustness()
