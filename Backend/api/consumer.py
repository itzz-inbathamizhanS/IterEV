"""
Consumer API — POST endpoints for the Consumer EV flow.

Endpoints:
  POST /api/consumer/routes      Generate candidate routes with computed values
  POST /api/consumer/feasibility Compute FMF/FMR for given EV state + trips
  GET  /api/consumer/demo        Return demo data clearly labelled as DEMO

Research flow implemented here (research doc §17 — End-to-End Workflow):
  Steps 1–12 for the consumer use case:
  1. EV state received (from request body)
  2. Current trip requirements received
  3. Future trips received
  4. Generate candidate routes (ROUTE_PROFILES from constants)
  5. Predict energy (energy_engine)
  6. Predict battery consequence (battery_engine)
  7. Project future state (battery_engine.future_soc_projection)
  8. [Skipped: future demand scenarios — Phase 3]
  9–10. Calculate FMF/FMR (feasibility_engine)
  11. Optimize (optimizer)
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
from engines.energy_engine import compute_all_routes
from engines.battery_engine import compute_soc_after, estimate_tomorrow_soc, estimate_range_km
from engines.feasibility_engine import compute_fmf, compute_risk_timeline, compute_full_feasibility
from engines.optimizer import select_recommended
from engines.explanation_engine import generate_explanation

router = APIRouter(prefix="/api/consumer", tags=["consumer"])


@router.post("/routes", response_model=list[RouteCandidate])
async def get_consumer_routes(req: ConsumerRoutesRequest) -> list[RouteCandidate]:
    """
    Generate candidate routes with fully computed energy, battery, and feasibility values.

    This is the primary Consumer flow endpoint — called when the user enters their
    EV state and destination, triggering the full 5-engine pipeline.
    """
    ev = req.evState

    # Step 5: Predict energy for each route under given conditions
    route_profiles = compute_all_routes(
        traffic=req.traffic,
        temperature=ev.temperature,
        soh=ev.soh,
    )

    # Steps 6–7 + 9–10: Battery consequence + feasibility for each route
    candidates: list[RouteCandidate] = []
    for profile in route_profiles:
        energy = profile["energy_kwh"]
        time_min = profile["time_min"]
        cost_inr = profile["cost_inr"]

        # Battery state transition
        soc_after = compute_soc_after(ev.soc, energy, ev.soh, ev.capacity_kwh)
        soc_tomorrow = estimate_tomorrow_soc(soc_after)

        # Future feasibility after this route
        fmf, fmr, _ = compute_fmf(
            soc_after=soc_after,
            soh=ev.soh,
            future_trips=req.futureTrips,
            capacity_kwh=ev.capacity_kwh,
        )

        candidates.append(RouteCandidate(
            id=profile["id"],
            name=profile["name"],
            time=time_min,
            cost=cost_inr,
            energy=energy,
            feasibility=fmf,
            fmr=fmr,
            after=soc_after,
            tomorrow=soc_tomorrow,
            recommended=False,  # set by optimizer below
            is_computed=True,
        ))

    # Step 11: Optimize — select recommended route using J(a)
    recommended_id, scores = select_recommended(candidates)

    # Mark recommended route and compute risk change vs fastest
    fastest = min(candidates, key=lambda r: r.time)
    for route in candidates:
        route.recommended = (route.id == recommended_id)

    recommended = next(r for r in candidates if r.recommended)

    # Step 12: Generate explanation
    explanation_data = generate_explanation(recommended, candidates)
    recommended.explanation = explanation_data["reason_text"]
    recommended.risk_change = explanation_data["risk_change"]

    return candidates


@router.post("/feasibility", response_model=FeasibilityResult)
async def get_consumer_feasibility(req: FeasibilityRequest) -> FeasibilityResult:
    """
    Compute FMF/FMR for a given EV state and future trip list.

    Used by FuturePage to display the feasibility score and risk timeline
    independent of route selection.
    """
    ev = req.evState
    soc = req.soc_after_override if req.soc_after_override is not None else ev.soc

    return compute_full_feasibility(
        soc_after=soc,
        soh=ev.soh,
        future_trips=req.futureTrips,
        capacity_kwh=ev.capacity_kwh,
        horizon_days=5,
    )


@router.get("/demo")
async def get_demo_data() -> dict:
    """
    Return clearly-labelled demo data.
    Used as frontend fallback when backend is not reachable.
    """
    return {
        "is_demo": True,
        "label": "SIMULATION EXAMPLE",
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
