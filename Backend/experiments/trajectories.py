"""
Future State Trajectory Export

Exports the matrix of future SOC timelines for the proposed route (first 100 scenarios)
to trajectories.csv for detailed visualization and inspection.
"""
import os
import csv
import logging
import numpy as np

from models.schemas import RouteCandidate
from engines.energy_engine import compute_all_routes
from engines.battery_engine import compute_soc_after, compute_soh_degradation
from engines.feasibility_engine import compute_probabilistic_fmr, _parse_day_index
from engines.uncertainty_engine import generate_scenarios, AblationFlags
from engines.optimizer import select_recommended

from experiments.risk_decomposition import EVState, FutureTrip

logger = logging.getLogger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
CSV_OUTPUT = os.path.join(RESULTS_DIR, "trajectories.csv")

def export_trajectories(
    soc: float = 80.0,
    soh: float = 95.0,
    temperature: float = 30.0,
    random_seed: int = 42,
    scenario_count: int = 100,
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
    
    # We will pick the IterEV recommended route.
    candidates = []
    for profile in route_profiles:
        energy = profile["energy_kwh"]
        soc_after = compute_soc_after(soc, energy, soh, capacity_kwh)
        soh_loss = compute_soh_degradation(
            energy_throughput_kwh=energy, temperature=temperature,
            soc_start=soc, soc_end=soc_after, capacity_kwh=capacity_kwh, soh=soh
        )
        soh_after = round(soh - soh_loss, 4)
        
        fmr_result = compute_probabilistic_fmr(
            soc_after=soc_after, soh=soh_after, future_trips=future_trips,
            capacity_kwh=capacity_kwh, efficiency_km_kwh=efficiency,
            scenario_count=scenario_count, random_seed=random_seed,
            planning_horizon=horizon
        )
        candidates.append(RouteCandidate(
            id=profile["id"], name=profile["name"], time=profile["time_min"], cost=profile["cost_inr"],
            energy=profile["energy_kwh"], feasibility=fmr_result.fmf, fmr=fmr_result.fmr, 
            after=soc_after, tomorrow=soc_after-5, recommended=False
        ))

    recommended_id, _, _ = select_recommended(candidates)
    selected_profile = next(p for p in route_profiles if p["id"] == recommended_id)
    
    # Now run the state propagation logic for just the recommended route and export
    energy = selected_profile["energy_kwh"]
    soc_after = compute_soc_after(soc, energy, soh, capacity_kwh)
    soh_loss = compute_soh_degradation(
        energy_throughput_kwh=energy, temperature=temperature,
        soc_start=soc, soc_end=soc_after, capacity_kwh=capacity_kwh, soh=soh
    )
    soh_after = round(soh - soh_loss, 4)

    # Simplified extraction of SOC trajectories since FeasibilityResult doesn't return it
    # We recreate the loops
    trip_days = [_parse_day_index(t.day) for t in future_trips]
    sim_horizon = max(max(trip_days) + 1 if trip_days else 0, horizon)
    
    scenarios = generate_scenarios(n_scenarios=scenario_count, horizon_days=sim_horizon, random_seed=random_seed)
    
    soc_arr = np.full(scenario_count, soc_after)
    soh_arr = np.full(scenario_count, soh_after)
    
    soc_by_day = np.zeros((scenario_count, sim_horizon + 1))
    soc_by_day[:, 0] = soc_after
    
    from engines.feasibility_engine import _compute_degradation_vec
    from engines.charging_engine import compute_soc_after_charging_vec
    from models.constants import (
        TEMP_SENSITIVITY_PER_DEGREE, BASELINE_TEMP_C, BASELINE_SOH,
        SOH_ENERGY_FACTOR_PER_POINT, SAFETY_SOC_BUFFER_PCT,
        MAX_SINGLE_CHARGE_KM, LONG_TRIP_DEPARTURE_SOC_MIN,
        DEFAULT_CHARGER_POWER_KW, CHARGING_EFFICIENCY, MAX_CHARGING_SOC,
        MIN_OPERATIONAL_SOC, DAILY_STANDBY_LOSS_PCT
    )

    trips_by_day = {}
    for i, trip in enumerate(future_trips):
        d = trip_days[i]
        trips_by_day.setdefault(d, []).append((i, trip))

    for day in range(sim_horizon):
        day_col = min(day, scenarios.energy_multipliers.shape[1] - 1)
        energy_mult = scenarios.energy_multipliers[:, day_col]
        temp_offset = scenarios.temperature_offsets[:, day_col]
        traffic_factor = scenarios.traffic_factors[:, day_col]
        charger_avail = scenarios.charger_available[:, day_col]
        deg_noise = scenarios.degradation_noise[:, day_col]
        demand_mult = scenarios.demand_multipliers[:, day_col]

        effective_temp = temperature + temp_offset
        temp_energy_factor = 1.0 + np.abs(effective_temp - BASELINE_TEMP_C) * TEMP_SENSITIVITY_PER_DEGREE
        soh_energy_factor = 1.0 + np.maximum(0.0, BASELINE_SOH - soh_arr) * SOH_ENERGY_FACTOR_PER_POINT
        combined_energy_factor = energy_mult * traffic_factor * temp_energy_factor * soh_energy_factor
        
        usable_kwh = capacity_kwh * (soh_arr / 100.0)
        safe_usable = np.maximum(usable_kwh, 0.01)

        if day in trips_by_day:
            for trip_idx, trip in trips_by_day[day]:
                adjusted_distance = trip.distance_km * demand_mult
                trip_energy = (adjusted_distance * combined_energy_factor) / efficiency
                trip_soc_consumption = (trip_energy / safe_usable) * 100.0
                
                soc_before_trip = soc_arr.copy()
                is_long = adjusted_distance > MAX_SINGLE_CHARGE_KM
                rng_enroute = np.random.RandomState(random_seed + day * 100 + trip_idx)
                enroute_charger_avail = rng_enroute.rand(scenario_count) < 0.5
                
                trip_energy_required = trip_energy + (SAFETY_SOC_BUFFER_PCT * safe_usable / 100.0)
                current_energy = (soc_before_trip * safe_usable / 100.0)
                required_charge = np.maximum(0.0, trip_energy_required - current_energy)
                maximum_charge = DEFAULT_CHARGER_POWER_KW * 0.5 * CHARGING_EFFICIENCY
                actual_charge = np.where(enroute_charger_avail & is_long, np.minimum(required_charge, maximum_charge), 0.0)
                
                soc_gain = (actual_charge / safe_usable) * 100.0
                soc_arr = np.minimum(MAX_CHARGING_SOC, soc_before_trip + soc_gain)
                soc_arr = np.maximum(0.0, soc_arr - trip_soc_consumption)
                
                delta_soh_trip = _compute_degradation_vec(
                    energy_kwh=trip_energy, temperature=effective_temp,
                    soc_start=soc_before_trip, soc_end=soc_arr, usable_kwh=safe_usable,
                    degradation_noise=deg_noise
                )
                soh_arr = np.maximum(0.0, soh_arr - delta_soh_trip)
                usable_kwh = capacity_kwh * (soh_arr / 100.0)
                safe_usable = np.maximum(usable_kwh, 0.01)
                
        charge_mask = charger_avail & (soc_arr < 80.0)
        if np.any(charge_mask):
            soc_before_charge = soc_arr.copy()
            soc_arr = compute_soc_after_charging_vec(soc_before=soc_arr, charging_duration_min=240.0, soh=soh_arr, charger_available=charge_mask, capacity_kwh=capacity_kwh)
            charge_energy = np.where(charge_mask, (soc_arr - soc_before_charge) / 100.0 * safe_usable, 0.0)
            delta_soh_charge = _compute_degradation_vec(
                energy_kwh=np.maximum(charge_energy, 0.0), temperature=effective_temp,
                soc_start=soc_before_charge, soc_end=soc_arr, usable_kwh=safe_usable, degradation_noise=deg_noise, charging_power_kw=DEFAULT_CHARGER_POWER_KW
            )
            soh_arr = np.maximum(0.0, soh_arr - delta_soh_charge)

        soc_arr = soc_arr - DAILY_STANDBY_LOSS_PCT
        soc_arr = np.clip(soc_arr, 0.0, 100.0)
        if day + 1 < soc_by_day.shape[1]:
            soc_by_day[:, day + 1] = soc_arr
            
    # Export to CSV
    export_count = min(scenario_count, 100)
    with open(CSV_OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["scenario_id"] + [f"day_{d}" for d in range(sim_horizon + 1)]
        writer.writerow(header)
        for i in range(export_count):
            row = [f"scenario_{i}"] + [round(val, 2) for val in soc_by_day[i]]
            writer.writerow(row)
            
    logger.info(f"Trajectories saved to {CSV_OUTPUT}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    export_trajectories()
