"""
Physical and operational constants for the Future-Mobility-Aware EV Decision System.

Research reference: Section 12 (Proposed Solution) and Section 14 (Mathematical Formulation)
of the Future-Mobility-Aware EV Research Project Full Document.

All constants are physically motivated. Sensitivity to these values is explored in
the simulation engine (Phase 3 ablation studies).
"""

# ─── Battery ─────────────────────────────────────────────────────────────────
NOMINAL_CAPACITY_KWH: float = 80.0          # Default large EV battery (kWh)
BASELINE_EFFICIENCY_KM_KWH: float = 6.0     # km per kWh at 25°C, medium traffic, flat road
BASELINE_SOH: float = 94.0                   # SOH at which base energy profiles are calibrated
BASELINE_TEMP_C: float = 29.0               # Temperature at which base profiles are calibrated (matches demo scenario)
SAFETY_SOC_BUFFER_PCT: float = 10.0         # Minimum SOC margin required above trip need
OVERNIGHT_LOSS_FACTOR: float = 0.09         # Fraction of SOC lost overnight (self-discharge + local use)

# Long trips (>MAX_SINGLE_CHARGE_KM) are assumed to include intermediate charging stops.
# Feasibility for these trips is evaluated on scheduling availability, not single-charge SOC.
# A CRITICAL trip to Chennai (500 km) requires charging en route — the EV can make the trip
# as long as charging infrastructure is available. We model this by requiring only ~20% SOC
# at departure as a "confidence buffer" for initiating the journey.
MAX_SINGLE_CHARGE_KM: float = 400.0         # km beyond which intermediate charging is assumed
LONG_TRIP_DEPARTURE_SOC_MIN: float = 20.0   # Minimum SOC to begin a long trip (charging en route)

# ─── Optimizer weights (from research doc §14) ─────────────────────────────
# min J(a) = CurrentCost(a) + LAMBDA·BatteryConsequence(a) + MU·FMR(a)
# These are defaults; sensitivity analysis should vary them across [0, 1].
LAMBDA_BATTERY: float = 0.30                 # Weight on battery consequence
MU_FMR: float = 0.50                         # Weight on future mobility risk

# ─── FMR threshold (chance constraint from §14) ─────────────────────────────
# FMR(a) ≤ EPSILON_FMR  →  maximum allowed future infeasibility probability
EPSILON_FMR: float = 0.10                    # 10% max allowed risk

# ─── Energy model sensitivity factors ───────────────────────────────────────
TRAFFIC_FACTORS: dict[str, float] = {
    "Low":    0.88,    # Free-flow highway, minimal stop-go
    "Medium": 1.00,    # Calibration baseline
    "High":   1.20,    # Dense urban/congested traffic
}

# Temperature effect: % energy change per °C deviation from 25°C
# Based on typical Li-ion battery efficiency curves
TEMP_SENSITIVITY_PER_DEGREE: float = 0.008  # 0.8% per °C

# SOH degradation effect: extra energy per SOH point below baseline
SOH_ENERGY_FACTOR_PER_POINT: float = 0.002  # 0.2% per SOH point below 94%

# ─── Priority weights for FMF calculation ───────────────────────────────────
PRIORITY_WEIGHTS: dict[str, float] = {
    "CRITICAL": 3.0,
    "HIGH":     2.0,
    "NORMAL":   1.0,
}

# ─── Route profiles for Coimbatore → Ooty (Phase 1 default scenario) ────────
# Base energy values are calibrated at: SOC=78%, SOH=94%, temp=29°C, traffic=Medium
# Distances reflect different route paths (highway vs. scenic vs. conservation)
ROUTE_PROFILES: list[dict] = [
    {
        "id": "01",
        "name": "FASTEST",
        "distance_km": 88.0,
        "base_time_min": 42,
        "base_cost_inr": 185,
        "base_energy_kwh": 14.8,   # Calibrated to produce ~58% SOC_after at defaults
        "time_traffic_mult": {"Low": 0.88, "Medium": 1.00, "High": 1.22},
        "cost_traffic_mult": {"Low": 0.95, "Medium": 1.00, "High": 1.08},
    },
    {
        "id": "02",
        "name": "FUTURE READY",
        "distance_km": 93.3,       # Slightly longer but gentler gradient
        "base_time_min": 48,
        "base_cost_inr": 172,
        "base_energy_kwh": 13.9,   # More efficient route despite longer distance
        "time_traffic_mult": {"Low": 0.90, "Medium": 1.00, "High": 1.18},
        "cost_traffic_mult": {"Low": 0.96, "Medium": 1.00, "High": 1.06},
    },
    {
        "id": "03",
        "name": "BATTERY CARE",
        "distance_km": 98.6,       # Longest but flattest gradient, slowest speed
        "base_time_min": 53,
        "base_cost_inr": 160,
        "base_energy_kwh": 13.1,   # Most efficient despite longest distance
        "time_traffic_mult": {"Low": 0.92, "Medium": 1.00, "High": 1.14},
        "cost_traffic_mult": {"Low": 0.97, "Medium": 1.00, "High": 1.04},
    },
]
