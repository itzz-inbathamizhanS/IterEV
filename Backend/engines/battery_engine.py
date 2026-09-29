"""
Battery Engine — Research Modules 1 + 3 (Current-state + Future-state engine).

Research reference:
  §12 §1 — Current-state engine: captures SoC, SoH, temperature, capacity.
  §12 §3 — Future-state engine: predicts future SoC/SoH distribution.
  §18    — State transition: x_(t+1) = F(x_t, a, ω)

Core formulas:
  SOC_after = SOC_initial − (E_route / C_usable) × 100
  C_usable  = C_nominal × (SOH / 100)
  SOC_next_day = SOC_current - DAILY_STANDBY_LOSS_PCT

Battery Degradation (reduced-order proxy model):
  ΔSOH = base_rate × throughput_factor × temp_factor × dod_factor × crate_factor
  SOH_next = SOH_current - ΔSOH

  This is NOT an electrochemical model. It is a parametric approximation
  suitable for planning-horizon simulations (days to weeks).

  Literature basis:
    - Xu et al. (2018), Journal of Power Sources — throughput dependence
    - Petit et al. (2016), Applied Energy — empirical aging model
    - Pelletier et al. (2017), Transportation Research Part B — degradation review
"""

from models.constants import (
    NOMINAL_CAPACITY_KWH,
    DAILY_STANDBY_LOSS_PCT,
    BASELINE_EFFICIENCY_KM_KWH,
    DEGRADATION_BASE_RATE,
    DEGRADATION_TEMP_REF_C,
    DEGRADATION_TEMP_COEFF,
    DEGRADATION_DOD_EXPONENT,
    DEGRADATION_CRATE_THRESHOLD,
    DEGRADATION_CRATE_COEFF,
)


def compute_usable_capacity(
    soh: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
) -> float:
    """
    Compute usable battery capacity based on SOH.

    Formula: C_usable = C_nominal × (SOH / 100)

    Args:
        soh: State of Health (%)
        capacity_kwh: Nominal battery capacity (kWh)

    Returns:
        Usable capacity (kWh).
    """
    return capacity_kwh * (soh / 100.0)


def compute_soc_after(
    soc_initial: float,
    energy_kwh: float,
    soh: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
) -> float:
    """
    Compute State of Charge after a trip.

    State transition: SOC_{t+1} = SOC_t - (E_route / C_usable) × 100

    Args:
        soc_initial: Starting SOC (%)
        energy_kwh: Energy consumed on the route (kWh)
        soh: Battery State of Health (%)
        capacity_kwh: Nominal battery capacity (kWh)

    Returns:
        SOC after trip (%), clamped to [0, 100], rounded to 1 dp.
    """
    usable_kwh = compute_usable_capacity(soh, capacity_kwh)
    if usable_kwh <= 0:
        return 0.0
    delta_soc_pct = (energy_kwh / usable_kwh) * 100.0
    soc_after = soc_initial - delta_soc_pct
    return round(max(0.0, min(100.0, soc_after)), 1)


def estimate_tomorrow_soc(soc_after: float) -> float:
    """
    Project SOC to the next day using the aggregate standby consumption model.

    This models the combined effect of:
      - Battery self-discharge (~0.1-0.3%/day for Li-ion)
      - Vehicle standby systems (BMS, 12V, thermal management)
      - Typical auxiliary loads

    The default DAILY_STANDBY_LOSS_PCT (5%) is an aggregate figure,
    NOT pure electrochemical self-discharge.

    Args:
        soc_after: SOC immediately after today's trip (%)

    Returns:
        Projected SOC at start of tomorrow (%), rounded to 1 dp.
    """
    soc_tomorrow = soc_after - DAILY_STANDBY_LOSS_PCT
    return round(max(0.0, soc_tomorrow), 1)


def compute_soh_degradation(
    energy_throughput_kwh: float,
    temperature: float,
    soc_start: float,
    soc_end: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    soh: float = 100.0,
    charging_power_kw: float = 0.0,
    degradation_noise: float = 1.0,
) -> float:
    """
    Compute SOH loss from a single trip or charging event.

    Reduced-order degradation model:
      ΔSOH = base_rate × throughput_factor × temp_factor × dod_factor × crate_factor × noise

    This is a parametric approximation, NOT an electrochemical model.

    Args:
        energy_throughput_kwh: Energy cycled through the battery (kWh)
        temperature: Battery temperature during event (°C)
        soc_start: SOC at start of event (%)
        soc_end: SOC at end of event (%)
        capacity_kwh: Nominal capacity (kWh)
        soh: Current SOH (%) — affects usable capacity for normalization
        charging_power_kw: If charging event, the charger power (kW).
                          0 for discharge events.
        degradation_noise: Multiplicative noise factor (default 1.0, no noise)

    Returns:
        SOH loss (positive value, in percentage points), rounded to 6 dp.
    """
    usable_kwh = compute_usable_capacity(soh, capacity_kwh)
    if usable_kwh <= 0 or energy_throughput_kwh <= 0:
        return 0.0

    # 1. Throughput factor: normalized energy throughput
    throughput_factor = energy_throughput_kwh / usable_kwh

    # 2. Temperature factor: Arrhenius-inspired acceleration above reference
    temp_delta = abs(temperature - DEGRADATION_TEMP_REF_C)
    temp_factor = 1.0 + DEGRADATION_TEMP_COEFF * temp_delta

    # 3. Depth of Discharge factor: deeper cycles cause more degradation
    dod = abs(soc_start - soc_end) / 100.0
    dod_factor = max(dod, 0.01) ** DEGRADATION_DOD_EXPONENT

    # 4. C-rate factor: high-power charging accelerates degradation
    c_rate = 0.0
    if charging_power_kw > 0 and usable_kwh > 0:
        c_rate = charging_power_kw / usable_kwh
    if c_rate > DEGRADATION_CRATE_THRESHOLD:
        crate_factor = 1.0 + DEGRADATION_CRATE_COEFF * (c_rate - DEGRADATION_CRATE_THRESHOLD)
    else:
        crate_factor = 1.0

    # Combined degradation
    delta_soh = (
        DEGRADATION_BASE_RATE
        * throughput_factor
        * temp_factor
        * dod_factor
        * crate_factor
        * degradation_noise
    )

    return round(max(0.0, delta_soh), 6)


def estimate_range_km(
    soc: float,
    soh: float,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    efficiency_km_kwh: float = BASELINE_EFFICIENCY_KM_KWH,
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
    usable_kwh = compute_usable_capacity(soh, capacity_kwh)
    available_kwh = usable_kwh * (soc / 100.0)
    return round(available_kwh * efficiency_km_kwh)


def future_soc_projection(
    soc_after: float,
    horizon_days: int,
    daily_usage_km: float = 0.0,
    efficiency_km_kwh: float = BASELINE_EFFICIENCY_KM_KWH,
    capacity_kwh: float = NOMINAL_CAPACITY_KWH,
    soh: float = 94.0,
    uncertainty: str = "Low",
) -> list[float]:
    """
    Project SOC over a multi-day horizon without charging.
    Used by feasibility_engine for deterministic risk timeline.

    Args:
        soc_after: SOC at end of today's trip (%)
        horizon_days: Number of future days to project
        daily_usage_km: Expected km driven per day
        efficiency_km_kwh: Vehicle efficiency (km/kWh)
        capacity_kwh: Nominal capacity (kWh)
        soh: SOH (%)
        uncertainty: Uncertainty level (unused in deterministic projection)

    Returns:
        List of projected SOC values for each future day (day 1 = tomorrow).
    """
    usable_kwh = compute_usable_capacity(soh, capacity_kwh)
    daily_energy_kwh = daily_usage_km / efficiency_km_kwh if efficiency_km_kwh > 0 else 0.0

    projections = []
    soc = soc_after
    for _ in range(horizon_days):
        # Standby loss (fixed percentage)
        soc -= DAILY_STANDBY_LOSS_PCT
        # Energy loss from daily use
        if usable_kwh > 0:
            energy_loss_pct = (daily_energy_kwh / usable_kwh) * 100.0
            soc -= energy_loss_pct
        soc = max(0.0, soc)
        projections.append(round(soc, 1))

    return projections
