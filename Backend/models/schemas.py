"""
Pydantic v2 data models for the IterEV Decision System.

Extended for research-grade implementation with:
- Probabilistic FMR with confidence intervals
- Scenario-based feasibility results
- Battery degradation tracking
- Charging model support
- Experiment configuration
"""

from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


class EVState(BaseModel):
    vehicle_id: str = "EV-001"
    soc: float = Field(ge=0, le=100)
    soh: float = Field(ge=0, le=100)
    temperature: float
    capacity_kwh: float = 80.0
    efficiency: float = 6.0  # km/kWh — used by all engines


class FutureTrip(BaseModel):
    id: str
    day: str                              # "TODAY", "TOMORROW", "DAY 3", "DAY 5", etc.
    origin: str
    destination: str
    distance_km: float = Field(ge=0)
    priority: str = "NORMAL"


class ConsumerRoutesRequest(BaseModel):
    evState: EVState
    origin: str = "Coimbatore"
    destination: str = "Ooty"
    distance_km: float = 88.0
    traffic: str = "Medium"
    futureTrips: List[FutureTrip] = []
    # Research parameters (optional, defaults from constants.py)
    scenario_count: Optional[int] = None
    random_seed: Optional[int] = None
    uncertainty_level: str = "Medium"
    charging_availability: Optional[float] = None
    planning_horizon: int = 5


class FeasibilityRequest(BaseModel):
    evState: EVState
    futureTrips: List[FutureTrip] = []
    soc_after_override: Optional[float] = None
    scenario_count: Optional[int] = None
    random_seed: Optional[int] = None
    uncertainty_level: str = "Medium"
    charging_availability: Optional[float] = None
    planning_horizon: int = 5


class SimulationInput(BaseModel):
    mode: str = "Consumer"
    horizon: int = Field(default=5, ge=1, le=30)
    soh: float = Field(default=94.0, ge=60, le=100)
    temperature: float = Field(default=29.0, ge=-10, le=55)
    traffic: str = "Medium"
    demand: str = "Medium"
    charging: str = "Normal"          # "Normal" | "Restricted"
    uncertainty: str = "Low"
    scenario_count: int = Field(default=1000, ge=100, le=50000)
    random_seed: int = 42
    charging_availability: float = Field(default=0.95, ge=0.0, le=1.0)
    soc_initial: float = Field(default=78.0, ge=0, le=100)


# ─── Result Models ──────────────────────────────────────────────────────────

class TripFeasibilityDetail(BaseModel):
    trip_id: str
    destination: str
    distance_km: float
    priority: str
    day_index: int = 0                    # Actual day offset (0=today, 1=tomorrow, etc.)
    soc_required: float
    soc_available: float
    margin: float
    feasible: bool


class ConfidenceInterval(BaseModel):
    """Binomial confidence interval for FMR estimate."""
    lower: float
    upper: float
    level: float = 0.95


class FeasibilityResult(BaseModel):
    fmf: float
    fmr: float
    risk_timeline: List[float]
    trip_details: List[TripFeasibilityDetail] = []
    is_computed: bool = True
    # Probabilistic extensions
    total_scenarios: int = 0
    successful_scenarios: int = 0
    failed_scenarios: int = 0
    confidence_interval: Optional[ConfidenceInterval] = None
    random_seed: Optional[int] = None


class RouteCandidate(BaseModel):
    id: str
    name: str
    time: int                             # Travel time (minutes)
    cost: int                             # Monetary cost (INR)
    energy: float                         # Energy consumption (kWh)
    feasibility: float                    # FMF %
    fmr: float                            # FMR %
    after: float                          # SOC after trip (%)
    tomorrow: float                       # Projected SOC next day (%)
    recommended: bool
    explanation: str = ""
    risk_change: str = ""
    is_computed: bool = True
    # Research extensions
    soh_after: float = 0.0                # SOH after trip considering degradation
    fmr_ci_lower: float = 0.0            # FMR confidence interval lower bound
    fmr_ci_upper: float = 0.0            # FMR confidence interval upper bound
    total_scenarios: int = 0
    constraint_feasible: bool = True      # Whether FMR ≤ ε
    constraint_relaxed: bool = False      # Whether constraint was relaxed


class DecisionResult(BaseModel):
    recommended: RouteCandidate
    all_routes: List[RouteCandidate]
    explanation: str
    fmf: float
    fmr: float
    risk_timeline: List[float]
    status: str = "FEASIBLE"              # "FEASIBLE" | "NO_FEASIBLE_ACTION" | "CONSTRAINT_RELAXED"
    minimum_fmr: float = 0.0
    constraint_violation: bool = False


class SimulationOutput(BaseModel):
    feasibility: float
    risk: float
    energy: float
    travelTime: int
    riskRange: float
    # Research extensions
    fmr_ci_lower: float = 0.0
    fmr_ci_upper: float = 0.0
    total_scenarios: int = 0
    soh_loss: float = 0.0


class MethodComparisonRow(BaseModel):
    method: str
    travelTime: int
    energy: float
    feasibility: float
    risk: float
    soh_loss: float = 0.0
    future_success_rate: float = 100.0
    constraint_violations: int = 0


class SimulationResult(BaseModel):
    primary: SimulationOutput
    comparison: List[MethodComparisonRow]
    is_computed: bool = True
    random_seed: int = 42
    scenario_count: int = 0


# ─── Experiment Models ──────────────────────────────────────────────────────

class ExperimentConfig(BaseModel):
    """Configuration for a single experiment run."""
    name: str
    scenario_count: int = 5000
    random_seed: int = 42
    soc_initial: float = 78.0
    soh: float = 94.0
    temperature: float = 29.0
    traffic: str = "Medium"
    demand: str = "Medium"
    uncertainty: str = "Medium"
    charging_availability: float = 0.95
    planning_horizon: int = 5
    capacity_kwh: float = 80.0
    efficiency: float = 6.0
    lambda_battery: float = 0.30
    mu_fmr: float = 0.50
    epsilon_fmr: float = 0.10
