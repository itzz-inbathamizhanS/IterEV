"""
Feasibility Engine — Probabilistic Future Mobility Risk (FMR) estimation.

Research reference:
  §13.1 — Future Mobility Feasibility (FMF)
  §13.2 — Future Mobility Risk (FMR) = P(future mobility infeasible)
  §18   — FMR(a) = P[I_future(a, ω) = 0]

CRITICAL IMPLEMENTATION NOTES (fixes from research audit):

  The Monte Carlo simulator now correctly implements the full state chain:

  For each scenario s = 1..N, for each day d = 0..horizon:
    1. Check if trip scheduled on day d
    2. Compute trip energy under scenario conditions
    3. Check feasibility: SOC_available >= SOC_required
    4. If feasible: subtract trip energy from SOC (STATE CHANGE)
    5. If infeasible: mark scenario as failed, continue for diagnostics
    6. Compute SOH degradation from trip energy throughput
    7. Update SOH (STATE CHANGE)
    8. Apply charging if charger available (via charging_engine)
    9. Compute SOH degradation from charging
    10. Apply standby/auxiliary loss
    11. Clamp SOC to [0, 100]
    12. Advance to next day

  This ensures:
    - Future trips CONSUME SOC (Bug #1 fix)
    - SOH PROPAGATES across days (Bug #2 fix)
    - Charging engine is ACTUALLY USED (Bug #3 fix)
    - Degradation noise is APPLIED (Bug #10 fix)
    - Long trips use energy-balance feasibility (Bug #18 fix)

  A scenario FAILS if at least one mandatory future trip cannot be
  completed while respecting the minimum SOC reserve.

  FMR = N_failed / N_total

  Confidence interval: Wilson score (better coverage near 0/1).
"""

import numpy as np
from scipy import stats as scipy_stats

from models.schemas import FutureTrip, TripFeasibilityDetail, FeasibilityResult, ConfidenceInterval
from models.constants import (
    NOMINAL_CAPACITY_KWH,
    BASELINE_EFFICIENCY_KM_KWH,
    SAFETY_SOC_BUFFER_PCT,
    PRIORITY_WEIGHTS,
    DAILY_STANDBY_LOSS_PCT,
    MAX_SINGLE_CHARGE_KM,
    LONG_TRIP_DEPARTURE_SOC_MIN,
    TEMP_SENSITIVITY_PER_DEGREE,
    BASELINE_TEMP_C,
    BASELINE_SOH,
    SOH_ENERGY_FACTOR_PER_POINT,
    DEFAULT_SCENARIO_COUNT,
    DEFAULT_RANDOM_SEED,
    DEFAULT_CHARGING_AVAILABILITY,
    CONFIDENCE_LEVEL,
    MAX_CHARGING_SOC,
    DEFAULT_CHARGER_POWER_KW,
    CHARGING_EFFICIENCY,
    MIN_OPERATIONAL_SOC,
    DEGRADATION_BASE_RATE,
    DEGRADATION_TEMP_REF_C,
    DEGRADATION_TEMP_COEFF,
    DEGRADATION_DOD_EXPONENT,
    DEGRADATION_CRATE_THRESHOLD,
    DEGRADATION_CRATE_COEFF,
)
from engines.battery_engine import (
    compute_usable_capacity,
    future_soc_projection,
)
from engines.charging_engine import compute_soc_after_charging_vec
from engines.uncertainty_engine import generate_scenarios, ScenarioSet, AblationFlags


# ─── Day Parsing ────────────────────────────────────────────────────────────

def _parse_day_index(day_str: str) -> int:
    """
    Convert day string to integer day offset.
    "TODAY" → 0, "TOMORROW" → 1, "DAY 3" → 2, "DAY N" → N-1
    """
    day_upper = day_str.strip().upper()
    if day_upper == "TODAY":
        return 0
    if day_upper == "TOMORROW":
        return 1
    if day_upper.startswith("DAY"):
        try:
            n = int(day_upper.replace("DAY", "").strip())
            return max(0, n - 1)
        except ValueError:
            return 1
    return 1


# ─── Vectorized SOH Degradation (inline for performance) ───────────────────

def _compute_degradation_vec(
    energy_kwh: np.ndarray,
    temperature: np.ndarray,
    soc_start: np.ndarray,
    soc_end: np.ndarray,
    usable_kwh: np.ndarray,
    degradation_noise: np.ndarray,
    charging_power_kw: float = 0.0,
) -> np.ndarray:
    """
    Vectorized SOH degradation calculation for N scenarios.

    ΔSOH = base_rate × throughput × temp_factor × dod_factor × crate_factor × noise

    Args all shape (N,). Returns ΔSOH shape (N,).
    """
    safe_usable = np.maximum(usable_kwh, 0.01)
    throughput = energy_kwh / safe_usable

    temp_delta = np.abs(temperature - DEGRADATION_TEMP_REF_C)
    temp_factor = 1.0 + DEGRADATION_TEMP_COEFF * temp_delta

    dod = np.abs(soc_start - soc_end) / 100.0
    dod_factor = np.maximum(dod, 0.01) ** DEGRADATION_DOD_EXPONENT

    if charging_power_kw > 0:
        c_rate = charging_power_kw / safe_usable
        crate_factor = np.where(
            c_rate > DEGRADATION_CRATE_THRESHOLD,
            1.0 + DEGRADATION_CRATE_COEFF * (c_rate - DEGRADATION_CRATE_THRESHOLD),
            1.0,
        )
    else:
        crate_factor = np.ones_like(energy_kwh)

    delta_soh = (
        DEGRADATION_BASE_RATE
        * throughput
        * temp_factor
        * dod_factor
        * crate_factor
        * degradation_noise
    )
    return np.maximum(delta_soh, 0.0)


# ─── Trip SOC Requirement ───────────────────────────────────────────────────

def _soc_required_for_trip(
    distance_km: float,
    soh: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    efficiency_km_kwh: float = BASELINE_EFFICIENCY_KM_KWH,
    buffer_pct: float = SAFETY_SOC_BUFFER_PCT,
) -> float:
    """Compute minimum SOC required to begin a trip (scalar version for display)."""
    if distance_km > MAX_SINGLE_CHARGE_KM:
        return LONG_TRIP_DEPARTURE_SOC_MIN
    usable_kwh = compute_usable_capacity(soh, capacity_kwh)
    if usable_kwh <= 0:
        return 95.0
    energy_kwh = distance_km / efficiency_km_kwh
    soc_needed = (energy_kwh / usable_kwh) * 100.0 + buffer_pct
    return round(min(95.0, soc_needed), 1)


# ─── Deterministic FMF/FMR (Legacy, preserved for baselines) ────────────────

def compute_fmf(
    soc_after: float,
    soh: float,
    future_trips: list[FutureTrip],
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    efficiency_km_kwh: float = BASELINE_EFFICIENCY_KM_KWH,
    safety_buffer_pct: float = SAFETY_SOC_BUFFER_PCT,
) -> tuple[float, float, list[TripFeasibilityDetail]]:
    """
    Deterministic FMF/FMR using weighted feasibility ratio.
    LEGACY — preserved for baseline comparisons only.
    FMF = Σ(w_i × I_i) / Σ(w_i)
    """
    if not future_trips:
        return 99.0, 1.0, []

    trip_details = []
    weighted_feasible = 0.0
    weighted_total = 0.0

    max_day = max(_parse_day_index(t.day) for t in future_trips)
    projected_socs = [soc_after] + future_soc_projection(
        soc_after=soc_after,
        horizon_days=max(max_day + 1, 1),
        soh=soh,
        capacity_kwh=capacity_kwh,
        efficiency_km_kwh=efficiency_km_kwh,
    )

    for trip in future_trips:
        day_idx = _parse_day_index(trip.day)
        if day_idx < len(projected_socs):
            available_soc = projected_socs[day_idx]
        else:
            available_soc = projected_socs[-1] if projected_socs else soc_after

        soc_required = _soc_required_for_trip(
            trip.distance_km, soh, capacity_kwh, efficiency_km_kwh, safety_buffer_pct
        )
        margin = available_soc - soc_required
        is_feasible = margin >= 0

        weight = PRIORITY_WEIGHTS.get(trip.priority, 1.0)
        weighted_total += weight
        if is_feasible:
            weighted_feasible += weight

        trip_details.append(TripFeasibilityDetail(
            trip_id=trip.id,
            destination=trip.destination,
            distance_km=trip.distance_km,
            priority=trip.priority,
            day_index=day_idx,
            soc_required=soc_required,
            soc_available=round(available_soc, 1),
            margin=round(margin, 1),
            feasible=is_feasible,
        ))

    fmf = (weighted_feasible / weighted_total * 100.0) if weighted_total > 0 else 99.0
    fmr = 100.0 - fmf
    return round(fmf, 1), round(fmr, 1), trip_details


# ─── Probabilistic FMR (Research Implementation) ───────────────────────────

def compute_probabilistic_fmr(
    soc_after: float,
    soh: float,
    future_trips: list[FutureTrip],
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    efficiency_km_kwh: float = BASELINE_EFFICIENCY_KM_KWH,
    safety_buffer_pct: float = SAFETY_SOC_BUFFER_PCT,
    scenario_count: int = DEFAULT_SCENARIO_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
    uncertainty_level: str = "Medium",
    demand_level: str = "Medium",
    charging_availability: float = DEFAULT_CHARGING_AVAILABILITY,
    temperature: float = 29.0,
    planning_horizon: int = 5,
    ablation: AblationFlags | None = None,
) -> FeasibilityResult:
    """
    Compute probabilistic FMR using Monte Carlo scenario simulation.

    FULL STATE PROPAGATION (corrected):
      For each scenario, for each day:
        1. If trip on this day → compute energy, check feasibility, subtract SOC
        2. Compute SOH degradation from trip
        3. If charger available → charge using energy-balance model
        4. Compute SOH degradation from charging
        5. Apply standby loss
        6. Advance to next day

    A scenario FAILS if ANY required future trip is infeasible.
    FMR(a) = failed_scenarios / total_scenarios
    """
    abl = ablation or AblationFlags()

    if not future_trips:
        return FeasibilityResult(
            fmf=100.0, fmr=0.0,
            risk_timeline=[0.0] * planning_horizon,
            trip_details=[], is_computed=True,
            total_scenarios=scenario_count,
            successful_scenarios=scenario_count,
            failed_scenarios=0,
            confidence_interval=ConfidenceInterval(lower=0.0, upper=0.0, level=CONFIDENCE_LEVEL),
            random_seed=random_seed,
        )

    # Parse day indices for all trips; build a lookup: day → list of (index, trip)
    trip_days = [_parse_day_index(t.day) for t in future_trips]
    max_day = max(trip_days) if trip_days else 0
    sim_horizon = max(max_day + 1, planning_horizon)

    trips_by_day: dict[int, list[tuple[int, FutureTrip]]] = {}
    for i, trip in enumerate(future_trips):
        d = trip_days[i]
        trips_by_day.setdefault(d, []).append((i, trip))

    # Generate scenarios
    scenarios = generate_scenarios(
        n_scenarios=scenario_count,
        horizon_days=sim_horizon,
        uncertainty_level=uncertainty_level,
        demand_level=demand_level,
        charging_availability=charging_availability,
        base_temperature=temperature,
        random_seed=random_seed,
        ablation=abl,
    )

    N = scenario_count
    n_trips = len(future_trips)

    # ─── State Arrays ───────────────────────────────────────────────────
    # SOC and SOH tracked per-scenario, evolving over time
    soc = np.full(N, soc_after)               # Current SOC (%)
    soh_arr = np.full(N, soh)                  # Current SOH (%)

    # Record SOC at start of each day for risk timeline
    soc_by_day = np.zeros((N, sim_horizon + 1))
    soc_by_day[:, 0] = soc_after

    # Tracking
    scenario_failed = np.zeros(N, dtype=bool)
    trip_failed_matrix = np.zeros((N, n_trips), dtype=bool)
    trip_soc_avail_matrix = np.zeros((N, n_trips))
    trip_soc_req_matrix = np.zeros((N, n_trips))

    # ─── Day-by-Day State Propagation ───────────────────────────────────
    for day in range(sim_horizon):
        day_col = min(day, scenarios.energy_multipliers.shape[1] - 1)

        # Per-scenario environment for this day
        energy_mult = scenarios.energy_multipliers[:, day_col]
        temp_offset = scenarios.temperature_offsets[:, day_col]
        traffic_factor = scenarios.traffic_factors[:, day_col]
        charger_avail = scenarios.charger_available[:, day_col]
        deg_noise = scenarios.degradation_noise[:, day_col]
        demand_mult = scenarios.demand_multipliers[:, day_col]

        effective_temp = temperature + temp_offset
        temp_energy_factor = 1.0 + np.abs(effective_temp - BASELINE_TEMP_C) * TEMP_SENSITIVITY_PER_DEGREE
        soh_energy_factor = 1.0 + np.maximum(0.0, BASELINE_SOH - soh_arr) * SOH_ENERGY_FACTOR_PER_POINT

        # Combined energy adjustment factor for this day
        combined_energy_factor = energy_mult * traffic_factor * temp_energy_factor * soh_energy_factor

        # Usable capacity (depends on current SOH — this is the causal chain)
        usable_kwh = capacity_kwh * (soh_arr / 100.0)
        safe_usable = np.maximum(usable_kwh, 0.01)

        # ── Step 1: Process trips scheduled on this day ─────────────
        if day in trips_by_day:
            for trip_idx, trip in trips_by_day[day]:
                # Trip distance with per-day demand uncertainty
                adjusted_distance = trip.distance_km * demand_mult

                # Trip energy under scenario conditions
                # E = distance / (base_efficiency / combined_factor)
                #   = distance * combined_factor / base_efficiency
                trip_energy = (adjusted_distance * combined_energy_factor) / efficiency_km_kwh

                # SOC consumption for this trip (as %) - PHYSICAL
                trip_soc_consumption = (trip_energy / safe_usable) * 100.0
                # Required SOC including safety reserve
                trip_soc_req_pct = trip_soc_consumption + safety_buffer_pct

                soc_before_trip = soc.copy()
                
                # For long trips: check if en-route charging can bridge the gap
                is_long = adjusted_distance > MAX_SINGLE_CHARGE_KM
                
                # Separate en-route charger availability to prevent double-dipping overnight chargers
                rng_enroute = np.random.RandomState(random_seed + day * 100 + trip_idx)
                enroute_charger_avail = rng_enroute.rand(N) < charging_availability

                # Step 1: trip_energy (already computed)
                # Step 2: energy_required_with_reserve
                trip_energy_required = trip_energy + (safety_buffer_pct * safe_usable / 100.0)
                
                # Step 3: energy_available_before_charge
                current_energy = (soc_before_trip * safe_usable / 100.0)
                
                # Step 4: required_charge
                required_charge = np.maximum(0.0, trip_energy_required - current_energy)
                
                # Step 5: maximum_charge (assume 30 min stop)
                available_time_hrs = 0.5
                maximum_charge = DEFAULT_CHARGER_POWER_KW * available_time_hrs * CHARGING_EFFICIENCY
                
                # Step 6 & 7: actual_charge (applied ONLY if long trip AND en-route charger available)
                actual_charge = np.where(enroute_charger_avail & is_long, np.minimum(required_charge, maximum_charge), 0.0)
                
                # Step 8: Apply actual charge to SOC
                soc_gain = (actual_charge / safe_usable) * 100.0
                soc = np.minimum(MAX_CHARGING_SOC, soc_before_trip + soc_gain)
                
                # Step 9: energy_available_after_charge
                energy_available_after_charge = (soc * safe_usable / 100.0)
                
                # Step 10: trip feasible if energy_available >= required
                departure_feasible = soc_before_trip >= LONG_TRIP_DEPARTURE_SOC_MIN
                long_trip_infeasible = (energy_available_after_charge < trip_energy_required) | ~departure_feasible
                
                trip_infeasible = np.where(is_long, long_trip_infeasible, soc < trip_soc_req_pct)

                # Also fail if SOC would drop below minimum operational level (0.0% is minimum operational)
                # Note: MIN_OPERATIONAL_SOC is usually 0, but this checks hard minimums
                soc_after_trip = soc - trip_soc_consumption
                trip_infeasible |= (soc_after_trip < MIN_OPERATIONAL_SOC)

                # Track scenario-level metrics
                # Diagnostics: `trip_soc_req_matrix` should represent required SOC before trip
                trip_failed_matrix[:, trip_idx] = trip_infeasible
                trip_soc_avail_matrix[:, trip_idx] = soc_before_trip
                trip_soc_req_matrix[:, trip_idx] = trip_soc_req_pct

                # Mark failed scenarios
                scenario_failed |= trip_infeasible

                # ── STATE CHANGE: subtract ONLY PHYSICAL trip energy from SOC ──
                # SAFETY_SOC_BUFFER_PCT must never be subtracted as physical energy
                soc = np.maximum(0.0, soc - trip_soc_consumption)

                # ── SOH degradation from trip ──
                if abl.use_battery_degradation:
                    delta_soh_trip = _compute_degradation_vec(
                        energy_kwh=trip_energy,
                        temperature=effective_temp,
                        soc_start=soc_before_trip,
                        soc_end=soc,
                        usable_kwh=safe_usable,
                        degradation_noise=deg_noise,
                    )
                    soh_arr = np.maximum(0.0, soh_arr - delta_soh_trip)
                    # Update usable capacity after degradation
                    usable_kwh = capacity_kwh * (soh_arr / 100.0)
                    safe_usable = np.maximum(usable_kwh, 0.01)

        # ── Step 2: Charging opportunity ────────────────────────────
        # Use authoritative charging engine 
        # Charge when: charger available AND SOC < 80%
        charge_mask = charger_avail & (soc < 80.0)
        if np.any(charge_mask):
            soc_before_charge = soc.copy()

            # Charging duration window (e.g., overnight ~4 hours)
            charging_duration_min = 4.0 * 60.0
            
            soc = compute_soc_after_charging_vec(
                soc_before=soc,
                charging_duration_min=charging_duration_min,
                soh=soh_arr,
                charger_available=charge_mask,
                capacity_kwh=capacity_kwh
            )

            # SOH degradation from charging
            if abl.use_battery_degradation:
                charge_energy = np.where(charge_mask, (soc - soc_before_charge) / 100.0 * safe_usable, 0.0)
                delta_soh_charge = _compute_degradation_vec(
                    energy_kwh=np.maximum(charge_energy, 0.0),
                    temperature=effective_temp,
                    soc_start=soc_before_charge,
                    soc_end=soc,
                    usable_kwh=safe_usable,
                    degradation_noise=deg_noise,
                    charging_power_kw=DEFAULT_CHARGER_POWER_KW,
                )
                soh_arr = np.maximum(0.0, soh_arr - delta_soh_charge)

        # ── Step 3: Standby/auxiliary consumption ───────────────────
        soc = soc - DAILY_STANDBY_LOSS_PCT
        soc = np.clip(soc, 0.0, 100.0)

        # Record SOC at start of next day
        if day + 1 < soc_by_day.shape[1]:
            soc_by_day[:, day + 1] = soc

    # ─── Compute FMR ────────────────────────────────────────────────────
    failed_count = int(np.sum(scenario_failed))
    successful_count = N - failed_count

    fmr_fraction = failed_count / N
    fmr_pct = round(fmr_fraction * 100.0, 2)
    fmf_pct = round(100.0 - fmr_pct, 2)

    # ─── Wilson Score Confidence Interval ───────────────────────────────
    ci_lower, ci_upper = _wilson_ci(failed_count, N, CONFIDENCE_LEVEL)
    ci_lower_pct = round(ci_lower * 100.0, 2)
    ci_upper_pct = round(ci_upper * 100.0, 2)

    # ─── Risk Timeline ──────────────────────────────────────────────────
    # risk_timeline[d] = fraction of scenarios where at least one mandatory
    # trip scheduled on or after day d is infeasible.
    risk_timeline = []
    for day in range(planning_horizon):
        trips_on_after = [i for i, d in enumerate(trip_days) if d >= day]
        if not trips_on_after:
            risk_timeline.append(0.0)
        else:
            # Check if any of these trips failed in each scenario
            failed_on_after = np.any(trip_failed_matrix[:, trips_on_after], axis=1)
            day_fmr = np.mean(failed_on_after) * 100.0
            risk_timeline.append(round(float(day_fmr), 1))

    # ─── Per-Trip Details (Probabilistic, for display) ──────────────────
    trip_details = []
    for i, trip in enumerate(future_trips):
        day_idx = _parse_day_index(trip.day)
        
        # Calculate actual probabilistic results from the simulation
        mean_soc_avail = float(np.mean(trip_soc_avail_matrix[:, i]))
        mean_soc_req = float(np.mean(trip_soc_req_matrix[:, i]))
        failure_prob = np.mean(trip_failed_matrix[:, i]) * 100.0
        
        trip_details.append(TripFeasibilityDetail(
            trip_id=trip.id,
            destination=trip.destination,
            distance_km=trip.distance_km,
            priority=trip.priority,
            day_index=day_idx,
            soc_required=round(mean_soc_req, 1),
            soc_available=round(mean_soc_avail, 1),
            margin=round(mean_soc_avail - mean_soc_req, 1),
            feasible=(failure_prob < 10.0), # Considered broadly feasible if <10% failure
        ))

    # ─── Failure Taxonomy ───
    taxonomy = {
        "Energy Starvation (Healthy Battery)": 0,
        "Severe Degradation + High Demand": 0,
        "General Infeasibility": 0
    }
    if failed_count > 0:
        failed_indices = np.where(scenario_failed)[0]
        for idx in failed_indices:
            final_soh = soh_arr[idx]
            avg_demand = float(np.mean(scenarios.demand_multipliers[idx]))
            if final_soh < 85.0 and avg_demand > 1.1:
                taxonomy["Severe Degradation + High Demand"] += 1
            elif final_soh >= 85.0:
                taxonomy["Energy Starvation (Healthy Battery)"] += 1
            else:
                taxonomy["General Infeasibility"] += 1

    return FeasibilityResult(
        fmf=fmf_pct,
        fmr=fmr_pct,
        risk_timeline=risk_timeline,
        trip_details=trip_details,
        is_computed=True,
        total_scenarios=N,
        successful_scenarios=successful_count,
        failed_scenarios=failed_count,
        confidence_interval=ConfidenceInterval(
            lower=ci_lower_pct, upper=ci_upper_pct, level=CONFIDENCE_LEVEL,
        ),
        random_seed=random_seed,
        failure_taxonomy=taxonomy,
    )

def _wilson_ci(
    successes: int,
    n: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """
    Wilson score confidence interval for a binomial proportion.
    Ref: Wilson, E.B. (1927), JASA.
    """
    if n == 0:
        return 0.0, 1.0
    p_hat = successes / n
    z = scipy_stats.norm.ppf(1 - (1 - confidence) / 2)
    z2 = z * z
    denominator = 1 + z2 / n
    center = (p_hat + z2 / (2 * n)) / denominator
    spread = z * np.sqrt((p_hat * (1 - p_hat) + z2 / (4 * n)) / n) / denominator
    lower = max(0.0, center - spread)
    upper = min(1.0, center + spread)
    return lower, upper


def _compute_risk_timeline(
    soc_by_day: np.ndarray,
    soh_final: np.ndarray,
    future_trips: list[FutureTrip],
    trip_days: list[int],
    planning_horizon: int,
    capacity_kwh: float,
    efficiency_km_kwh: float,
    safety_buffer_pct: float,
    scenarios: ScenarioSet,
    temperature: float,
) -> list[float]:
    """
    Compute daily FMR values from the simulated SOC trajectories.
    For each day: fraction of scenarios where remaining trips are infeasible.
    """
    N = soc_by_day.shape[0]
    risk_by_day = []

    for day in range(planning_horizon):
        trips_up_to_day = [(i, t) for i, t in enumerate(future_trips) if trip_days[i] <= day]
        if not trips_up_to_day:
            risk_by_day.append(0.0)
            continue

        failed_up_to_day = np.zeros(N, dtype=bool)
        for i, trip in trips_up_to_day:
            trip_day = trip_days[i]
            if trip_day >= soc_by_day.shape[1]:
                continue
            soc_avail = soc_by_day[:, trip_day]
            # Use per-scenario SOH for timeline
            usable_kwh = capacity_kwh * (soh_final / 100.0)
            usable_kwh = np.maximum(usable_kwh, 0.01)

            day_col = min(trip_day, scenarios.demand_multipliers.shape[1] - 1)
            adjusted_dist = trip.distance_km * scenarios.demand_multipliers[:, day_col]
            energy_needed = adjusted_dist / efficiency_km_kwh
            soc_needed = np.where(
                adjusted_dist > MAX_SINGLE_CHARGE_KM,
                LONG_TRIP_DEPARTURE_SOC_MIN,
                (energy_needed / usable_kwh) * 100.0 + safety_buffer_pct,
            )
            soc_needed = np.clip(soc_needed, 0.0, 95.0)
            failed_up_to_day |= (soc_avail < soc_needed)

        fmr_day = np.sum(failed_up_to_day) / N * 100.0
        risk_by_day.append(round(fmr_day, 1))

    return risk_by_day


# ─── Legacy Wrappers (preserve existing API) ────────────────────────────────

def compute_risk_timeline(
    soc_after: float,
    soh: float,
    future_trips: list[FutureTrip],
    horizon_days: int = 5,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    efficiency_km_kwh: float = BASELINE_EFFICIENCY_KM_KWH,
    safety_buffer_pct: float = SAFETY_SOC_BUFFER_PCT,
) -> list[float]:
    """Deterministic daily FMR (legacy)."""
    risk_by_day = []
    projected_socs = [soc_after] + future_soc_projection(
        soc_after, horizon_days - 1, soh=soh, capacity_kwh=capacity_kwh,
        efficiency_km_kwh=efficiency_km_kwh,
    )
    for day_idx, soc_at_day in enumerate(projected_socs[:horizon_days]):
        remaining_trips = [t for t in future_trips if _parse_day_index(t.day) >= day_idx]
        _, fmr, _ = compute_fmf(
            soc_at_day, soh, remaining_trips,
            capacity_kwh, efficiency_km_kwh, safety_buffer_pct
        )
        risk_by_day.append(fmr)
    return risk_by_day


def compute_full_feasibility(
    soc_after: float,
    soh: float,
    future_trips: list[FutureTrip],
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    horizon_days: int = 5,
    efficiency_km_kwh: float = BASELINE_EFFICIENCY_KM_KWH,
    scenario_count: int = DEFAULT_SCENARIO_COUNT,
    random_seed: int = DEFAULT_RANDOM_SEED,
    uncertainty_level: str = "Medium",
    charging_availability: float = DEFAULT_CHARGING_AVAILABILITY,
    temperature: float = 29.0,
    ablation: AblationFlags | None = None,
) -> FeasibilityResult:
    """Primary research API — probabilistic FMR with full state propagation."""
    return compute_probabilistic_fmr(
        soc_after=soc_after,
        soh=soh,
        future_trips=future_trips,
        capacity_kwh=capacity_kwh,
        efficiency_km_kwh=efficiency_km_kwh,
        scenario_count=scenario_count,
        random_seed=random_seed,
        uncertainty_level=uncertainty_level,
        charging_availability=charging_availability,
        temperature=temperature,
        planning_horizon=horizon_days,
        ablation=ablation,
    )
