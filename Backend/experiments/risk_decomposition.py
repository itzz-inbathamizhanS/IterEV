"""
Risk Decomposition Engine

Estimates the contribution of individual uncertainty sources to the total FMR
using controlled ablation.

For each route, we calculate:
ΔFMR_component = FMR_without_component - FMR_full

This represents the 'controlled component sensitivity'.
"""
import os
import csv
import json
import logging
from typing import Any

from models.schemas import ConsumerRoutesRequest, EVState, FutureTrip
from engines.uncertainty_engine import AblationFlags
from engines.energy_engine import compute_all_routes
from engines.battery_engine import compute_soc_after, compute_soh_degradation
from engines.feasibility_engine import compute_probabilistic_fmr

logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CSV_OUTPUT = os.path.join(RESULTS_DIR, "risk_decomposition.csv")

def run_risk_decomposition(
    soc: float = 75.0,
    soh: float = 95.0,
    temperature: float = 30.0,
    random_seed: int = 42,
    scenario_count: int = 5000,
    horizon: int = 3,
):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    ev = EVState(
        soc=soc,
        soh=soh,
        capacity_kwh=50.0,
        efficiency=6.5,
        temperature=temperature
    )
    
    future_trips = [
        FutureTrip(id="f1", day="TOMORROW", origin="Home", destination="Remote", distance_km=150.0, priority="HIGH"),
        FutureTrip(id="f2", day="DAY 2", origin="Remote", destination="Office", distance_km=250.0, priority="CRITICAL"),
        FutureTrip(id="f3", day="DAY 3", origin="Office", destination="Home", distance_km=50.0, priority="NORMAL"),
    ]

    # Pre-compute routes
    route_profiles = compute_all_routes(
        traffic="Medium",
        temperature=temperature,
        soh=soh,
    )

    variants = [
        ("Full Model", AblationFlags()),
        ("No energy uncertainty", AblationFlags(use_energy_uncertainty=False)),
        ("No temperature uncertainty", AblationFlags(use_temperature_uncertainty=False)),
        ("No traffic uncertainty", AblationFlags(use_traffic_uncertainty=False)),
        ("No demand uncertainty", AblationFlags(use_demand_uncertainty=False)),
        ("No charging uncertainty", AblationFlags(use_charging_uncertainty=False)),
        ("No degradation uncertainty", AblationFlags(use_degradation_uncertainty=False)),
        ("No battery degradation", AblationFlags(use_battery_degradation=False)),
    ]

    results = []

    for route_idx, profile in enumerate(route_profiles):
        energy = profile["energy_kwh"]
        soc_after = compute_soc_after(soc, energy, soh, ev.capacity_kwh)
        soh_loss = compute_soh_degradation(
            energy_throughput_kwh=energy,
            temperature=temperature,
            soc_start=soc,
            soc_end=soc_after,
            capacity_kwh=ev.capacity_kwh,
            soh=soh,
        )
        soh_after = round(soh - soh_loss, 4)

        # Baseline (Full Model)
        baseline_result = compute_probabilistic_fmr(
            soc_after=soc_after,
            soh=soh_after,
            future_trips=future_trips,
            capacity_kwh=ev.capacity_kwh,
            efficiency_km_kwh=ev.efficiency,
            scenario_count=scenario_count,
            random_seed=random_seed,
            uncertainty_level="High",  # Stress uncertainty to see effects
            planning_horizon=horizon,
            ablation=AblationFlags()
        )
        baseline_fmr = baseline_result.fmr

        for variant_name, abl_flags in variants:
            if variant_name == "Full Model":
                continue

            variant_result = compute_probabilistic_fmr(
                soc_after=soc_after,
                soh=soh_after,
                future_trips=future_trips,
                capacity_kwh=ev.capacity_kwh,
                efficiency_km_kwh=ev.efficiency,
                scenario_count=scenario_count,
                random_seed=random_seed,
                uncertainty_level="High",
                planning_horizon=horizon,
                ablation=abl_flags
            )

            delta_fmr = variant_result.fmr - baseline_fmr
            ci = variant_result.confidence_interval

            results.append({
                "route": profile["name"],
                "baseline_fmr": baseline_fmr,
                "component": variant_name,
                "variant_fmr": variant_result.fmr,
                "delta_fmr": round(delta_fmr, 2),
                "ci_lower": ci.lower if ci else 0.0,
                "ci_upper": ci.upper if ci else 0.0,
                "scenario_count": scenario_count,
                "seed": random_seed
            })

    with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "route", "baseline_fmr", "component", "variant_fmr", "delta_fmr",
            "ci_lower", "ci_upper", "scenario_count", "seed"
        ])
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"Risk decomposition saved to {CSV_OUTPUT}")
    return results

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_risk_decomposition()
