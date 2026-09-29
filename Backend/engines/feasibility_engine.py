"""
Feasibility Engine — Probabilistic Future Mobility Risk (FMR) estimation.

Research reference:
  §13.1 — Future Mobility Feasibility (FMF):
           "probability that all planned trips in the next planning horizon can be
           completed, including required charging stops."
  §13.2 — Future Mobility Risk (FMR):
           FMR = P(future mobility requirements become infeasible)
  §18   — FMR(a) = P[I_future(a, ω) = 0]

Implementation:
  Phase 1 (legacy): Deterministic weighted feasibility (preserved for comparison)
  Phase 2 (research): Monte Carlo scenario-based probabilistic FMR

  For each candidate action a:
    1. Generate N future scenarios (via uncertainty_engine)
    2. For each scenario, propagate battery state through future days
    3. For each future trip, check feasibility under scenario conditions
    4. A scenario fails if ANY required trip is infeasible
    5. FMR(a) = failed_scenarios / total_scenarios
    6. Compute binomial confidence interval

  Confidence interval: Wilson score interval (better coverage than Wald for
  extreme proportions near 0 or 1).
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
    DEFAULT_SCENARIO_COUNT,
    DEFAULT_RANDOM_SEED,
    DEFAULT_CHARGING_AVAILABILITY,
    CONFIDENCE_LEVEL,
    MAX_CHARGING_SOC,
)
from engines.battery_engine import (
    compute_usable_capacity,
    compute_soh_degradation,
    future_soc_projection,
)
from engines.uncertainty_engine import generate_scenarios, ScenarioSet


# ─── Day Parsing ────────────────────────────────────────────────────────────

def _parse_day_index(day_str: str) -> int:
    """
    Convert day string to integer day offset.

    "TODAY"     → 0
    "TOMORROW"  → 1
    "DAY 3"     → 2  (day 3 = index 2, since day 1 = index 0 is today)
    "DAY 5"     → 4
    "DAY N"     → N-1

    This fixes the previous implementation which used trip list index
    instead of actual day parsing.
    """
    day_upper = day_str.strip().upper()
    if day_upper == "TODAY":
        return 0
    if day_upper == "TOMORROW":
        return 1
    # Parse "DAY N" format
    if day_upper.startswith("DAY"):
        try:
            n = int(day_upper.replace("DAY", "").strip())
            return max(0, n - 1)  # DAY 1 = today = index 0
        except ValueError:
            return 1  # Default to tomorrow if unparseable
    return 1  # Default


# ─── Trip SOC Requirement ───────────────────────────────────────────────────

def _soc_required_for_trip(
    distance_km: float,
    soh: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    efficiency_km_kwh: float = BASELINE_EFFICIENCY_KM_KWH,
    buffer_pct: float = SAFETY_SOC_BUFFER_PCT,
) -> float:
    """
    Compute the minimum SOC required to begin a trip.

    For SHORT trips (≤ MAX_SINGLE_CHARGE_KM):
      SOC_required = (E_trip / C_usable × 100) + buffer_pct
      where E_trip = distance_km / efficiency_km_kwh

    For LONG trips (> MAX_SINGLE_CHARGE_KM):
      Requires en-route charging. Minimum departure SOC only.
    """
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
    Calculate deterministic FMF/FMR using weighted feasibility ratio.

    This is the LEGACY implementation preserved for baseline comparisons.
    For research use, prefer compute_probabilistic_fmr().

    FMF = Σ(w_i × I_i) / Σ(w_i)
    """
    if not future_trips:
        return 99.0, 1.0, []

    trip_details = []
    weighted_feasible = 0.0
    weighted_total = 0.0

    # Project SOC forward using day indices
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

        # Use projected SOC for the correct day
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
) -> FeasibilityResult:
    """
    Compute probabilistic FMR using Monte Carlo scenario simulation.

    For each candidate action a:
      1. Generate N future scenarios
      2. For each scenario, propagate battery state day-by-day
      3. For each future trip at its scheduled day, check feasibility
      4. A scenario fails if ANY required trip is infeasible
      5. FMR(a) = failed_scenarios / total_scenarios
      6. Compute Wilson score confidence interval

    Args:
        soc_after: SOC after the current action (%)
        soh: Current SOH (%)
        future_trips: Planned future trips
        capacity_kwh: Nominal battery capacity (kWh)
        efficiency_km_kwh: Vehicle efficiency (km/kWh)
        safety_buffer_pct: Safety SOC margin (%)
        scenario_count: Number of Monte Carlo scenarios (N)
        random_seed: For reproducibility
        uncertainty_level: "Low" | "Medium" | "High"
        demand_level: "Low" | "Medium" | "High" | "Very High"
        charging_availability: P(charger available) for Bernoulli
        temperature: Base temperature (°C)
        planning_horizon: Number of future days

    Returns:
        FeasibilityResult with probabilistic FMR, confidence interval,
        scenario counts, and per-trip details.
    """
    if not future_trips:
        return FeasibilityResult(
            fmf=99.0, fmr=1.0,
            risk_timeline=[1.0] * planning_horizon,
            trip_details=[], is_computed=True,
            total_scenarios=scenario_count,
            successful_scenarios=scenario_count,
            failed_scenarios=0,
            confidence_interval=ConfidenceInterval(lower=0.0, upper=2.0 / scenario_count * 100),
            random_seed=random_seed,
        )

    # Parse day indices for all trips
    trip_days = [_parse_day_index(t.day) for t in future_trips]
    max_day = max(trip_days) if trip_days else 0
    sim_horizon = max(max_day + 1, planning_horizon)

    # Generate scenarios
    scenarios = generate_scenarios(
        n_scenarios=scenario_count,
        horizon_days=sim_horizon,
        uncertainty_level=uncertainty_level,
        demand_level=demand_level,
        charging_availability=charging_availability,
        base_temperature=temperature,
        random_seed=random_seed,
    )

    # ─── Vectorized Scenario Simulation ─────────────────────────────────
    N = scenario_count

    # Initialize SOC array: (N,) — all scenarios start at soc_after
    soc_by_day = np.full((N, sim_horizon + 1), soc_after)
    soh_current = np.full(N, soh)

    # Propagate SOC day by day
    for day in range(sim_horizon):
        # Standby loss
        soc_by_day[:, day + 1] = soc_by_day[:, day] - DAILY_STANDBY_LOSS_PCT

        # Temperature-adjusted efficiency for this day
        day_idx = min(day, scenarios.temperature_offsets.shape[1] - 1)
        temp_offsets = scenarios.temperature_offsets[:, day_idx]
        effective_temp = temperature + temp_offsets
        temp_factor = 1.0 + (effective_temp - BASELINE_TEMP_C) * TEMP_SENSITIVITY_PER_DEGREE

        # Traffic factor for this day
        traffic_factors = scenarios.traffic_factors[:, day_idx]

        # Energy multiplier (prediction uncertainty)
        energy_mult = scenarios.energy_multipliers[:, day_idx]

        # Combined efficiency adjustment
        combined_factor = temp_factor * traffic_factors * energy_mult

        # Check if charging is available this day
        charger_avail = scenarios.charger_available[:, day_idx]

        # For scenarios where charger IS available and SOC < 50%, assume opportunity charging
        # This models overnight/daytime charging opportunity
        charge_mask = charger_avail & (soc_by_day[:, day + 1] < 50.0)
        # Charge up to 80% SOC (partial charge during available window)
        soc_by_day[charge_mask, day + 1] = np.minimum(
            80.0, soc_by_day[charge_mask, day + 1] + 30.0
        )

        # Clamp SOC
        soc_by_day[:, day + 1] = np.clip(soc_by_day[:, day + 1], 0.0, 100.0)

    # ─── Check Trip Feasibility Per Scenario ────────────────────────────
    # A scenario fails if ANY required trip is infeasible
    scenario_failed = np.zeros(N, dtype=bool)

    # Per-trip aggregated feasibility for reporting
    trip_feasible_counts = np.zeros(len(future_trips), dtype=int)

    for i, trip in enumerate(future_trips):
        day_idx = trip_days[i]

        # Get SOC available on the trip's day for all scenarios
        soc_available = soc_by_day[:, day_idx]

        # Adjust trip distance by demand multiplier
        adjusted_distance = trip.distance_km * scenarios.demand_multipliers

        # Compute SOC required with per-scenario efficiency variation
        day_col = min(day_idx, sim_horizon - 1)
        energy_mult = scenarios.energy_multipliers[:, day_col]
        traffic_factor = scenarios.traffic_factors[:, day_col]
        temp_offset = scenarios.temperature_offsets[:, day_col]
        effective_temp = temperature + temp_offset
        temp_factor = 1.0 + (effective_temp - BASELINE_TEMP_C) * TEMP_SENSITIVITY_PER_DEGREE

        # Effective efficiency per scenario (km/kWh)
        effective_efficiency = efficiency_km_kwh / (energy_mult * traffic_factor * temp_factor)
        effective_efficiency = np.clip(effective_efficiency, 1.0, 20.0)

        # For long trips: check departure SOC + charging availability
        is_long_trip = adjusted_distance > MAX_SINGLE_CHARGE_KM
        usable_kwh = capacity_kwh * (soh_current / 100.0)

        # Short trip: energy-based SOC requirement
        energy_needed = adjusted_distance / effective_efficiency
        soc_needed = np.where(
            is_long_trip,
            LONG_TRIP_DEPARTURE_SOC_MIN,
            (energy_needed / usable_kwh) * 100.0 + safety_buffer_pct,
        )
        soc_needed = np.clip(soc_needed, 0.0, 95.0)

        # For long trips, also check charging availability
        long_trip_charger = scenarios.charger_available[:, day_col]
        trip_infeasible = soc_available < soc_needed
        # Long trips fail if charger unavailable AND SOC insufficient
        trip_infeasible = np.where(
            is_long_trip,
            trip_infeasible & ~long_trip_charger,
            trip_infeasible,
        )

        trip_feasible = ~trip_infeasible
        trip_feasible_counts[i] = np.sum(trip_feasible)

        # Mark scenarios as failed if this trip is infeasible
        scenario_failed |= trip_infeasible

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

    # ─── Per-Trip Feasibility Details (deterministic, for display) ──────
    _, _, trip_details = compute_fmf(
        soc_after, soh, future_trips,
        capacity_kwh, efficiency_km_kwh, safety_buffer_pct,
    )
    # Enrich with scenario-based success rates
    for i, detail in enumerate(trip_details):
        if i < len(trip_feasible_counts):
            scenario_rate = trip_feasible_counts[i] / N * 100.0
            # Update margin to reflect probabilistic assessment
            detail.margin = round(scenario_rate - 50.0, 1)

    # ─── Risk Timeline ──────────────────────────────────────────────────
    risk_timeline = _compute_risk_timeline_from_scenarios(
        soc_by_day, soh, future_trips, trip_days, planning_horizon,
        capacity_kwh, efficiency_km_kwh, safety_buffer_pct, scenarios, temperature,
    )

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
    )


def _wilson_ci(
    successes: int,
    n: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """
    Wilson score confidence interval for a binomial proportion.

    Better coverage than the Wald interval for proportions near 0 or 1.

    Ref: Wilson, E.B. (1927), "Probable inference, the law of succession,
         and statistical inference", JASA.

    Args:
        successes: Number of "successes" (here: failed scenarios)
        n: Total number of trials (scenarios)
        confidence: Confidence level (default 0.95)

    Returns:
        (lower, upper) bounds of the confidence interval.
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


def _compute_risk_timeline_from_scenarios(
    soc_by_day: np.ndarray,
    soh: float,
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
    Compute daily FMR values from scenario simulation results.

    For each day in the horizon, compute the fraction of scenarios
    where at least one remaining trip (from that day forward) is infeasible.
    """
    N = soc_by_day.shape[0]
    risk_by_day = []

    for day in range(planning_horizon):
        # Find trips from this day forward
        remaining = [(i, t) for i, t in enumerate(future_trips) if trip_days[i] >= day]

        if not remaining:
            risk_by_day.append(0.0)
            continue

        # For each remaining trip, check feasibility in all scenarios
        failed_in_day = np.zeros(N, dtype=bool)

        for i, trip in remaining:
            trip_day = trip_days[i]
            if trip_day >= soc_by_day.shape[1]:
                continue

            soc_avail = soc_by_day[:, trip_day]
            usable_kwh = capacity_kwh * (soh / 100.0)
            if usable_kwh <= 0:
                failed_in_day[:] = True
                continue

            adjusted_dist = trip.distance_km * scenarios.demand_multipliers
            energy_needed = adjusted_dist / efficiency_km_kwh
            soc_needed = np.where(
                adjusted_dist > MAX_SINGLE_CHARGE_KM,
                LONG_TRIP_DEPARTURE_SOC_MIN,
                (energy_needed / usable_kwh) * 100.0 + safety_buffer_pct,
            )
            soc_needed = np.clip(soc_needed, 0.0, 95.0)
            failed_in_day |= (soc_avail < soc_needed)

        fmr_day = np.sum(failed_in_day) / N * 100.0
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
    """
    Compute daily FMR values across a planning horizon (deterministic).
    Legacy API — preserved for backward compatibility.
    """
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
) -> FeasibilityResult:
    """
    Full feasibility computation using probabilistic FMR.

    This is the primary research API. Uses Monte Carlo scenario simulation
    to compute probabilistic FMR with confidence intervals.
    """
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
    )
