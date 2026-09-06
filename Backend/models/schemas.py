"""
Pydantic v2 data models for the Future-Mobility-Aware EV Decision System.
Uses pydantic v2 (installed via pip install pydantic>=2.0.0).
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
    efficiency: float = 6.0


class FutureTrip(BaseModel):
    id: str
    day: str
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


class FeasibilityRequest(BaseModel):
    evState: EVState
    futureTrips: List[FutureTrip] = []
    soc_after_override: Optional[float] = None


class SimulationInput(BaseModel):
    mode: str = "Consumer"
    horizon: int = Field(default=5, ge=1, le=30)
    soh: float = Field(default=94.0, ge=60, le=100)
    temperature: float = Field(default=29.0, ge=15, le=48)
    traffic: str = "Medium"
    demand: str = "Medium"
    charging: str = "Normal"
    uncertainty: str = "Low"


class TripFeasibilityDetail(BaseModel):
    trip_id: str
    destination: str
    distance_km: float
    priority: str
    soc_required: float
    soc_available: float
    margin: float
    feasible: bool


class FeasibilityResult(BaseModel):
    fmf: float
    fmr: float
    risk_timeline: List[float]
    trip_details: List[TripFeasibilityDetail] = []
    is_computed: bool = True


class RouteCandidate(BaseModel):
    id: str
    name: str
    time: int
    cost: int
    energy: float
    feasibility: float
    fmr: float
    after: float
    tomorrow: float
    recommended: bool
    explanation: str = ""
    risk_change: str = ""
    is_computed: bool = True


class DecisionResult(BaseModel):
    recommended: RouteCandidate
    all_routes: List[RouteCandidate]
    explanation: str
    fmf: float
    fmr: float
    risk_timeline: List[float]


class SimulationOutput(BaseModel):
    feasibility: float
    risk: float
    energy: float
    travelTime: int
    riskRange: float


class MethodComparisonRow(BaseModel):
    method: str
    travelTime: int
    energy: float
    feasibility: float
    risk: float


class SimulationResult(BaseModel):
    primary: SimulationOutput
    comparison: List[MethodComparisonRow]
    is_computed: bool = True
