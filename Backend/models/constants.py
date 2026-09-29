"""
Physical and operational constants for the IterEV Decision System.

Research reference: Section 12 (Proposed Solution) and Section 14 (Mathematical Formulation).

All constants are physically motivated. Sensitivity to these values is explored
in the experiment framework (sensitivity analysis and ablation studies).

IMPORTANT: This is the single authoritative source for all model parameters.
No magic numbers should exist outside this file.
"""

# ─── Battery ─────────────────────────────────────────────────────────────────
NOMINAL_CAPACITY_KWH: float = 80.0          # Default large EV battery (kWh)
BASELINE_EFFICIENCY_KM_KWH: float = 6.0     # km per kWh at 25°C, medium traffic, flat road
BASELINE_SOH: float = 94.0                  # SOH at which base energy profiles are calibrated
BASELINE_TEMP_C: float = 29.0               # Temperature at which base profiles are calibrated
SAFETY_SOC_BUFFER_PCT: float = 10.0         # Minimum SOC margin required above trip need
MIN_OPERATIONAL_SOC: float = 5.0            # Absolute minimum SOC for safe operation (%)

# ─── Overnight / Standby Model ──────────────────────────────────────────────
# This is an AGGREGATE STANDBY CONSUMPTION model, NOT pure self-discharge.
# Components:
#   - Battery self-discharge: ~0.1-0.3% per day (Li-ion, ref: Redondo-Iglesias et al., 2018)
#   - Vehicle standby systems: ~0.5-1.5% per day (BMS, 12V system, thermal management)
#   - Typical auxiliary loads: ~2-5% per day (cabin preconditioning, scheduled tasks)
# Total: ~3-7% per day depending on vehicle and configuration.
# We use 5% as the default aggregate daily standby consumption.
# This is explicitly NOT pure electrochemical self-discharge.
DAILY_STANDBY_LOSS_PCT: float = 5.0         # % of SOC lost per day from standby consumption

# ─── Long trip thresholds ────────────────────────────────────────────────────
# Trips > MAX_SINGLE_CHARGE_KM require intermediate charging stops.
MAX_SINGLE_CHARGE_KM: float = 400.0
LONG_TRIP_DEPARTURE_SOC_MIN: float = 20.0   # Minimum SOC to begin a long trip

# ─── Optimizer weights (from research doc §14) ─────────────────────────────
# min J(a) = CurrentCost(a) + LAMBDA·BatteryConsequence(a) + MU·FMR(a)
# subject to: FMR(a) ≤ EPSILON_FMR
LAMBDA_BATTERY: float = 0.30                 # Weight on battery consequence
MU_FMR: float = 0.50                         # Weight on future mobility risk
EPSILON_FMR: float = 0.10                    # 10% max allowed FMR (chance constraint)

# ─── Energy model sensitivity factors ───────────────────────────────────────
TRAFFIC_FACTORS: dict[str, float] = {
    "Low":    0.88,    # Free-flow highway, minimal stop-go
    "Medium": 1.00,    # Calibration baseline
    "High":   1.20,    # Dense urban/congested traffic
}

# Temperature effect: % energy change per °C deviation from BASELINE_TEMP_C
# Based on typical Li-ion battery efficiency curves.
# Ref: Steinstraeter et al. (2021), "Effect of Low Temperature on EV Range"
# Both extreme heat and cold increase consumption due to HVAC and battery inefficiency.
TEMP_SENSITIVITY_PER_DEGREE: float = 0.008  # 0.8% per °C

# SOH degradation effect: extra energy per SOH point below baseline
# Ref: Barré et al. (2013), "A review on lithium-ion battery ageing mechanisms"
SOH_ENERGY_FACTOR_PER_POINT: float = 0.002  # 0.2% per SOH point below 94%

# ─── Priority weights for FMF calculation ───────────────────────────────────
PRIORITY_WEIGHTS: dict[str, float] = {
    "CRITICAL": 3.0,
    "HIGH":     2.0,
    "NORMAL":   1.0,
}

# ─── Battery Degradation Model ──────────────────────────────────────────────
# Reduced-order / proxy degradation model.
# NOT an electrochemical model. This is a parametric approximation suitable for
# planning-horizon simulations (days to weeks), not cycle-level predictions.
#
# ΔSOH = base_rate × throughput_factor × temperature_factor × dod_factor × crate_factor
#
# Ref (conceptual basis):
#   - Xu et al. (2018), "Modeling the effect of two-stage fast charging on
#     lithium iron phosphate battery degradation", Journal of Power Sources
#   - Petit et al. (2016), "Development of an empirical aging model for Li-ion
#     batteries and application to assess the impact of V2G strategies on
#     battery lifetime", Applied Energy
#   - Pelletier et al. (2017), "Battery degradation and behaviour for electric
#     vehicles: Review and numerical analyses of several models", Transportation Research Part B
#
# These references motivate the functional form (throughput, DoD, temperature, C-rate).
# The specific coefficient values below are order-of-magnitude calibrated for
# an 80 kWh NMC-type automotive battery pack.
DEGRADATION_BASE_RATE: float = 0.0001        # Base SOH loss per unit normalized throughput
DEGRADATION_TEMP_REF_C: float = 25.0         # Reference temperature for degradation
DEGRADATION_TEMP_COEFF: float = 0.06         # Arrhenius-inspired: per °C above ref
DEGRADATION_DOD_EXPONENT: float = 1.2        # DoD power-law exponent
DEGRADATION_CRATE_THRESHOLD: float = 1.0     # C-rate above which extra degradation occurs
DEGRADATION_CRATE_COEFF: float = 0.3         # Extra degradation per C-rate above threshold

# ─── Charging Model ─────────────────────────────────────────────────────────
DEFAULT_CHARGER_POWER_KW: float = 50.0       # Default DC fast charger power (kW)
CHARGING_EFFICIENCY: float = 0.92            # Charging efficiency (wall-to-battery)
DEFAULT_CHARGING_COST_PER_KWH: float = 15.0  # INR per kWh (Indian context)
MAX_CHARGING_SOC: float = 95.0              # Maximum SOC from charging (%)

# ─── Uncertainty Engine Parameters ──────────────────────────────────────────
# Energy prediction uncertainty
# Ref: De Cauwer et al. (2015), "Energy Consumption Prediction for Electric
#   Vehicles Based on Real-World Data", Energies — shows 5-15% prediction error
ENERGY_UNCERTAINTY_SIGMA: dict[str, float] = {
    "Low":    0.03,   # σ = 3% — well-known route, good conditions
    "Medium": 0.08,   # σ = 8% — typical prediction uncertainty
    "High":   0.15,   # σ = 15% — poor conditions, unknown route
}

# Temperature variability
TEMPERATURE_VARIABILITY_STD: dict[str, float] = {
    "Low":    1.0,    # ±1°C
    "Medium": 3.0,    # ±3°C
    "High":   6.0,    # ±6°C
}

# Traffic probability distributions
TRAFFIC_DISTRIBUTIONS: dict[str, dict[str, float]] = {
    "Low": {"Low": 0.70, "Medium": 0.25, "High": 0.05},
    "Medium": {"Low": 0.20, "Medium": 0.55, "High": 0.25},
    "High": {"Low": 0.05, "Medium": 0.30, "High": 0.65},
}

# Future demand scaling
DEMAND_MULTIPLIER: dict[str, float] = {
    "Low":       0.7,
    "Medium":    1.0,
    "High":      1.4,
    "Very High": 1.8,
}

# Default charging availability (Bernoulli probability)
DEFAULT_CHARGING_AVAILABILITY: float = 0.95

# ─── Monte Carlo / Scenario Sampling ────────────────────────────────────────
DEFAULT_SCENARIO_COUNT: int = 5000
DEFAULT_RANDOM_SEED: int = 42
CONFIDENCE_LEVEL: float = 0.95              # For confidence interval calculation

# ─── Route profiles for Coimbatore → Ooty (Research Scenario) ───────────────
# Base energy values are calibrated at: SOC=78%, SOH=94%, temp=29°C, traffic=Medium
# These are RESEARCH SCENARIO profiles, not real-time routing data.
ROUTE_PROFILES: list[dict] = [
    {
        "id": "01",
        "name": "FASTEST",
        "distance_km": 88.0,
        "base_time_min": 42,
        "base_cost_inr": 185,
        "base_energy_kwh": 14.8,
        "time_traffic_mult": {"Low": 0.88, "Medium": 1.00, "High": 1.22},
        "cost_traffic_mult": {"Low": 0.95, "Medium": 1.00, "High": 1.08},
    },
    {
        "id": "02",
        "name": "FUTURE READY",
        "distance_km": 93.3,
        "base_time_min": 48,
        "base_cost_inr": 172,
        "base_energy_kwh": 13.9,
        "time_traffic_mult": {"Low": 0.90, "Medium": 1.00, "High": 1.18},
        "cost_traffic_mult": {"Low": 0.96, "Medium": 1.00, "High": 1.06},
    },
    {
        "id": "03",
        "name": "BATTERY CARE",
        "distance_km": 98.6,
        "base_time_min": 53,
        "base_cost_inr": 160,
        "base_energy_kwh": 13.1,
        "time_traffic_mult": {"Low": 0.92, "Medium": 1.00, "High": 1.14},
        "cost_traffic_mult": {"Low": 0.97, "Medium": 1.00, "High": 1.04},
    },
]
