"""
Feasibility Engine — Research Module 5 (Decision engine, future mobility component).

Research reference:
  §13.1 — Future Mobility Feasibility (FMF):
           "probability that all planned trips in the next planning horizon can be
           completed, including required charging stops."

  §13.2 — Future Mobility Risk (FMR):
           FMR = P(future mobility requirements become infeasible)
           Simple definition: FMR = 1 − FMF

  §18    — Feasibility indicator:
           I_future(a, ω) = 1 if all required future trips/tasks can be completed; else 0
           FMR(a) = P[I_future(a, ω) = 0]

Implementation for Phase 1 (deterministic):
  - No Monte Carlo sampling (ω is treated as deterministic)
  - FMF computed as weighted fraction of feasible trips
  - Priority weights: CRITICAL=3.0, HIGH=2.0, NORMAL=1.0
  - Safety buffer = 10% SOC above bare minimum needed
"""

from models.schemas import FutureTrip, TripFeasibilityDetail, FeasibilityResult
from models.constants import (
    NOMINAL_CAPACITY_KWH,
    BASELINE_EFFICIENCY_KM_KWH,
    SAFETY_SOC_BUFFER_PCT,
    PRIORITY_WEIGHTS,
    OVERNIGHT_LOSS_FACTOR,
    MAX_SINGLE_CHARGE_KM,
    LONG_TRIP_DEPARTURE_SOC_MIN,
)
from engines.battery_engine import future_soc_projection


def _soc_required_for_trip(
    distance_km: float,
    soh: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    efficiency_km_kwh: float = BASELINE_EFFICIENCY_KM_KWH,
    buffer_pct: float = SAFETY_SOC_BUFFER_PCT,
) -> float:
    """
    Compute the minimum SOC required to begin a trip.

    For SHORT trips (≤ MAX_SINGLE_CHARGE_KM = 400 km):
      SOC_required = (E_trip / C_usable × 100) + buffer_pct

    For LONG trips (> MAX_SINGLE_CHARGE_KM):
      The trip requires intermediate charging stops.
      We require only LONG_TRIP_DEPARTURE_SOC_MIN (20%) to initiate the journey —
      the EV will charge en route. Feasibility depends on charging availability,
      not single-charge SOC. This is the standard EV practice for long-distance travel.
    """
    if distance_km > MAX_SINGLE_CHARGE_KM:
        # Long trip: requires en-route charging. Minimum departure SOC.
        return LONG_TRIP_DEPARTURE_SOC_MIN

    usable_kwh = capacity_kwh * (soh / 100.0)
    if usable_kwh <= 0:
        return 95.0
    energy_kwh = distance_km / efficiency_km_kwh
    soc_needed = (energy_kwh / usable_kwh) * 100.0 + buffer_pct
    return round(min(95.0, soc_needed), 1)



def compute_fmf(
    soc_after: float,
    soh: float,
    future_trips: list[FutureTrip],
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    efficiency_km_kwh: float = BASELINE_EFFICIENCY_KM_KWH,
    safety_buffer_pct: float = SAFETY_SOC_BUFFER_PCT,
) -> tuple[float, float, list[TripFeasibilityDetail]]:
    """
    Calculate Future Mobility Feasibility (FMF) and Future Mobility Risk (FMR).

    FMF = Σ(w_i × I_i) / Σ(w_i)  where w_i = priority weight, I_i = feasibility indicator

    Args:
        soc_after: SOC after today's trip (the battery state consequence of action a)
        soh: State of Health (%)
        future_trips: List of planned future trips
        capacity_kwh: Battery capacity (kWh)
        efficiency_km_kwh: km/kWh baseline
        safety_buffer_pct: Safety margin (%)

    Returns:
        Tuple of (FMF%, FMR%, list of per-trip details)
    """
    if not future_trips:
        return 99.0, 1.0, []

    trip_details = []
    weighted_feasible = 0.0
    weighted_total = 0.0

    # For multi-day trips: project battery forward
    # Day index derived from trip.day field
    soc_projections: dict[str, float] = {}
    projected_socs = future_soc_projection(
        soc_after=soc_after,
        horizon_days=len(future_trips) + 1,
        soh=soh,
        capacity_kwh=capacity_kwh,
    )

    for idx, trip in enumerate(future_trips):
        # Use projected SOC for multi-day trips
        # TODAY trip → use soc_after directly
        # Future days → use projection
        if trip.day.upper() == "TODAY":
            available_soc = soc_after
        else:
            # Use projected SOC for day (index 0 = tomorrow)
            proj_idx = min(idx, len(projected_socs) - 1)
            available_soc = projected_socs[proj_idx] if projected_socs else soc_after

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
            soc_required=soc_required,
            soc_available=round(available_soc, 1),
            margin=round(margin, 1),
            feasible=is_feasible,
        ))

    fmf = (weighted_feasible / weighted_total * 100.0) if weighted_total > 0 else 99.0
    fmr = 100.0 - fmf
    return round(fmf, 1), round(fmr, 1), trip_details


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
    Compute daily FMR values across a planning horizon.
    Used by FuturePage and RiskPage to display the risk timeline.

    For each day, compute the FMF assuming the battery state continues
    to decline via overnight loss, and evaluate remaining feasibility.

    Args:
        soc_after: SOC after today's trip
        soh: Battery health
        future_trips: All planned future trips
        horizon_days: Number of days to project

    Returns:
        List of FMR% values for [today, day1, day2, ..., day(horizon-1)]
    """
    risk_by_day = []
    projected_socs = [soc_after] + future_soc_projection(
        soc_after, horizon_days - 1, soh=soh, capacity_kwh=capacity_kwh
    )

    for day_idx, soc_at_day in enumerate(projected_socs[:horizon_days]):
        # Only evaluate trips from this day forward
        remaining_trips = [
            t for i, t in enumerate(future_trips)
            if i >= day_idx or t.day.upper() == "TODAY"
        ]
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
) -> FeasibilityResult:
    """
    Full feasibility computation — FMF, FMR, risk timeline, and per-trip details.
    Called by POST /api/consumer/feasibility.

    Args:
        soc_after: SOC after today's candidate action
        soh: Battery health
        future_trips: Planned future trips
        capacity_kwh: Battery capacity
        horizon_days: Risk timeline length

    Returns:
        FeasibilityResult with all computed values.
    """
    fmf, fmr, trip_details = compute_fmf(soc_after, soh, future_trips, capacity_kwh)
    risk_timeline = compute_risk_timeline(
        soc_after, soh, future_trips, horizon_days, capacity_kwh
    )
    return FeasibilityResult(
        fmf=fmf,
        fmr=fmr,
        risk_timeline=risk_timeline,
        trip_details=trip_details,
        is_computed=True,
    )
