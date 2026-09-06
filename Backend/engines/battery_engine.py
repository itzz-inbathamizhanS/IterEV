"""
Battery Engine — Research Modules 1 + 3 (Current-state engine + Future-state engine).

Research reference:
  §12 §1 — Current-state engine: captures SoC, SoH, temperature, capacity.
  §12 §3 — Future-state engine: predicts a distribution/range of future SoC/SoH.
  §18    — State transition: x_(t+1) = F(x_t, a, ω)

Core formulas:
  SOC_after = SOC_initial − (E_route / C_usable) × 100
  C_usable  = C_nominal × (SOH / 100)
  SOC_tomorrow = SOC_after × (1 − OVERNIGHT_LOSS_FACTOR)
"""

from models.constants import NOMINAL_CAPACITY_KWH, OVERNIGHT_LOSS_FACTOR


def compute_soc_after(
    soc_initial: float,
    energy_kwh: float,
    soh: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
) -> float:
    """
    Compute State of Charge after a trip.

    State transition: x_(t+1) = F(x_t, a, ω)
    For deterministic Phase 1: ω is ignored (no uncertainty sampling).

    Args:
        soc_initial: Starting SOC (%)
        energy_kwh: Energy consumed on the route (kWh)
        soh: Battery State of Health (%)
        capacity_kwh: Nominal battery capacity (kWh)

    Returns:
        SOC after trip (%), clamped to [0, 100], rounded to 1 dp.
    """
    usable_kwh = capacity_kwh * (soh / 100.0)
    if usable_kwh <= 0:
        return 0.0
    delta_soc_pct = (energy_kwh / usable_kwh) * 100.0
    soc_after = soc_initial - delta_soc_pct
    return round(max(0.0, min(100.0, soc_after)), 1)


def estimate_tomorrow_soc(soc_after: float) -> float:
    """
    Project SOC to the next day, assuming no overnight charging.
    Models self-discharge (~0.5%/day) + local errands / auxiliary loads.

    Conservative model (safety-first for feasibility calculation):
    loss = 9% of current SOC.

    Args:
        soc_after: SOC immediately after today's trip (%)

    Returns:
        Projected SOC at start of tomorrow (%), rounded to 1 dp.
    """
    loss = soc_after * OVERNIGHT_LOSS_FACTOR
    return round(max(0.0, soc_after - loss), 1)


def estimate_range_km(
    soc: float,
    soh: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    efficiency_km_kwh: float = 6.0,
) -> int:
    """
    Estimate current range.

    Args:
        soc: Current SOC (%)
        soh: State of Health (%)
        capacity_kwh: Nominal battery capacity (kWh)
        efficiency_km_kwh: Baseline efficiency (km/kWh)

    Returns:
        Estimated range (km), rounded to nearest integer.
    """
    usable_kwh = capacity_kwh * (soh / 100.0)
    available_kwh = usable_kwh * (soc / 100.0)
    return round(available_kwh * efficiency_km_kwh)


def future_soc_projection(
    soc_after: float,
    horizon_days: int,
    daily_usage_km: float = 0.0,
    efficiency_km_kwh: float = 6.0,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    soh: float = 94.0,
    uncertainty: str = "Low",
) -> list[float]:
    """
    Project SOC over a multi-day horizon without charging.
    Used by feasibility_engine to compute per-day risk.

    Args:
        soc_after: SOC at end of today's trip (%)
        horizon_days: Number of future days to project
        daily_usage_km: Expected km driven per day (default 0 = self-discharge only)
        uncertainty: "Low" | "Medium" | "High" — widens the projection range

    Returns:
        List of projected SOC values for each future day (day 1 = tomorrow).
    """
    usable_kwh = capacity_kwh * (soh / 100.0)
    # Daily energy from local use
    daily_energy_kwh = daily_usage_km / efficiency_km_kwh if efficiency_km_kwh > 0 else 0.0
    # Self-discharge only (no daily use passed from caller)
    daily_loss_pct = OVERNIGHT_LOSS_FACTOR * 100  # 9% per day

    projections = []
    soc = soc_after
    for _ in range(horizon_days):
        # Loss from self-discharge
        soc_loss = soc * (OVERNIGHT_LOSS_FACTOR)
        # Loss from daily energy use (if any)
        energy_loss_pct = (daily_energy_kwh / usable_kwh * 100) if usable_kwh > 0 else 0
        soc = max(0.0, soc - soc_loss - energy_loss_pct)
        projections.append(round(soc, 1))

    return projections
