"""
Consumer API — POST endpoints for the Consumer EV flow.

Endpoints:
  POST /api/consumer/routes      Generate candidate routes with probabilistic FMR
  POST /api/consumer/feasibility Compute probabilistic FMF/FMR for given EV state + trips
  GET  /api/consumer/demo        Return demo data clearly labelled as DEMO

Research flow (§17 — End-to-End Workflow):
  1. EV state received (from request body)
  2. Current trip requirements received
  3. Future trips received
  4. Generate candidate routes (ROUTE_PROFILES)
  5. Predict energy (energy_engine)
  6. Predict battery consequence (battery_engine) — including SOH degradation
  7. Project future state (battery_engine + uncertainty_engine)
  8. Generate future scenarios (uncertainty_engine)
  9–10. Calculate probabilistic FMF/FMR (feasibility_engine)
  11. Optimize with constraint enforcement (optimizer)
  12. Return decision + explanation (explanation_engine)
"""

from fastapi import APIRouter
from models.schemas import (
    ConsumerRoutesRequest,
    FeasibilityRequest,
    RouteCandidate,
    DecisionResult,
    FeasibilityResult,
)
from models.constants import (
    DEFAULT_SCENARIO_COUNT,
    DEFAULT_RANDOM_SEED,
    DEFAULT_CHARGING_AVAILABILITY,
)
from engines.energy_engine import compute_all_routes
from engines.battery_engine import (
    compute_soc_after,
    estimate_tomorrow_soc,
    estimate_range_km,
    compute_soh_degradation,
)
from engines.feasibility_engine import (
    compute_fmf,
    compute_probabilistic_fmr,
    compute_full_feasibility,
)
from engines.optimizer import select_recommended
from engines.explanation_engine import generate_explanation

router = APIRouter(prefix="/api/consumer", tags=["consumer"])


@router.post("/routes", response_model=list[RouteCandidate])
async def get_consumer_routes(req: ConsumerRoutesRequest) -> list[RouteCandidate]:
    """
    Generate candidate routes with fully computed energy, battery, and
    probabilistic feasibility values.

    This is the primary Consumer flow endpoint — called when the user enters their
    EV state and destination, triggering the full engine pipeline including
    Monte Carlo FMR estimation.
    """
    ev = req.evState
    scenario_count = req.scenario_count or DEFAULT_SCENARIO_COUNT
    random_seed = req.random_seed if req.random_seed is not None else DEFAULT_RANDOM_SEED
    charging_avail = req.charging_availability if req.charging_availability is not None else DEFAULT_CHARGING_AVAILABILITY

    # Step 5: Predict energy for each route under given conditions
    route_profiles = compute_all_routes(
        traffic=req.traffic,
        temperature=ev.temperature,
        soh=ev.soh,
    )

    # Steps 6–10: Battery consequence + probabilistic feasibility for each route
    candidates: list[RouteCandidate] = []
    for i, profile in enumerate(route_profiles):
        energy = profile["energy_kwh"]
        time_min = profile["time_min"]
        cost_inr = profile["cost_inr"]

        # Battery state transition (SOC)
        soc_after = compute_soc_after(ev.soc, energy, ev.soh, ev.capacity_kwh)
        soc_tomorrow = estimate_tomorrow_soc(soc_after)

        # Battery degradation (SOH) for this trip
        soh_loss = compute_soh_degradation(
            energy_throughput_kwh=energy,
            temperature=ev.temperature,
            soc_start=ev.soc,
            soc_end=soc_after,
            capacity_kwh=ev.capacity_kwh,
            soh=ev.soh,
        )
        soh_after = round(ev.soh - soh_loss, 4)

        # Probabilistic FMR with scenario simulation
        # Use per-route seed offset for independence between route evaluations
        route_seed = random_seed + i
        fmr_result = compute_probabilistic_fmr(
            soc_after=soc_after,
            soh=soh_after,
            future_trips=req.futureTrips,
            capacity_kwh=ev.capacity_kwh,
            efficiency_km_kwh=ev.efficiency,
            scenario_count=scenario_count,
            random_seed=route_seed,
            uncertainty_level=req.uncertainty_level,
            charging_availability=charging_avail,
            temperature=ev.temperature,
            planning_horizon=req.planning_horizon,
        )

        ci = fmr_result.confidence_interval

        candidates.append(RouteCandidate(
            id=profile["id"],
            name=profile["name"],
            time=time_min,
            cost=cost_inr,
            energy=energy,
            feasibility=fmr_result.fmf,
            fmr=fmr_result.fmr,
            after=soc_after,
            tomorrow=soc_tomorrow,
            recommended=False,
            is_computed=True,
            soh_after=soh_after,
            fmr_ci_lower=ci.lower if ci else 0.0,
            fmr_ci_upper=ci.upper if ci else 0.0,
            total_scenarios=fmr_result.total_scenarios,
        ))

    # Step 11: Optimize — select recommended route using J(a) with constraint
    recommended_id, scores, status = select_recommended(candidates)

    # Mark recommended route and set constraint flags
    for route in candidates:
        route.recommended = (route.id == recommended_id)
        score = next((s for s in scores if s.route_id == route.id), None)
        if score:
            route.constraint_feasible = score.feasible
        if route.recommended and status == "NO_FEASIBLE_ACTION":
            route.constraint_relaxed = True

    recommended = next(r for r in candidates if r.recommended)

    # Step 12: Generate explanation
    explanation_data = generate_explanation(recommended, candidates)
    recommended.explanation = explanation_data["reason_text"]
    recommended.risk_change = explanation_data["risk_change"]

    # If no feasible action, append warning to explanation
    if status == "NO_FEASIBLE_ACTION":
        recommended.explanation += (
            f" WARNING: All routes exceed the FMR constraint "
            f"(minimum FMR: {min(r.fmr for r in candidates):.1f}%). "
            f"This route was selected with constraint relaxation."
        )

    return candidates


@router.post("/feasibility", response_model=FeasibilityResult)
async def get_consumer_feasibility(req: FeasibilityRequest) -> FeasibilityResult:
    """
    Compute probabilistic FMF/FMR for a given EV state and future trip list.

    Uses Monte Carlo scenario simulation with configurable parameters.
    """
    ev = req.evState
    soc = req.soc_after_override if req.soc_after_override is not None else ev.soc
    scenario_count = req.scenario_count or DEFAULT_SCENARIO_COUNT
    random_seed = req.random_seed if req.random_seed is not None else DEFAULT_RANDOM_SEED
    charging_avail = req.charging_availability if req.charging_availability is not None else DEFAULT_CHARGING_AVAILABILITY

    return compute_full_feasibility(
        soc_after=soc,
        soh=ev.soh,
        future_trips=req.futureTrips,
        capacity_kwh=ev.capacity_kwh,
        horizon_days=req.planning_horizon,
        efficiency_km_kwh=ev.efficiency,
        scenario_count=scenario_count,
        random_seed=random_seed,
        uncertainty_level=req.uncertainty_level,
        charging_availability=charging_avail,
        temperature=ev.temperature,
    )


@router.get("/demo")
async def get_demo_data() -> dict:
    """
    Return clearly-labelled demo data.
    Used as frontend fallback when backend is not reachable.
    """
    return {
        "is_demo": True,
        "label": "DEMO DATA — Not from research engine",
        "routes": [
            {"id": "01", "name": "FASTEST", "time": 42, "cost": 185, "energy": 14.8,
             "feasibility": 94.0, "fmr": 6.0, "after": 58.0, "tomorrow": 52.8,
             "recommended": False, "is_computed": False},
            {"id": "02", "name": "FUTURE READY", "time": 48, "cost": 172, "energy": 13.9,
             "feasibility": 98.0, "fmr": 2.0, "after": 61.0, "tomorrow": 55.5,
             "recommended": True, "is_computed": False},
            {"id": "03", "name": "BATTERY CARE", "time": 53, "cost": 160, "energy": 13.1,
             "feasibility": 99.0, "fmr": 1.0, "after": 64.0, "tomorrow": 58.2,
             "recommended": False, "is_computed": False},
        ],
    }
