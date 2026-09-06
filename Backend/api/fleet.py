"""
Fleet API — Stub for Phase 2.

Fleet flow (research doc §15 — Fleet Architecture):
  Fleet state → Task manager → Demand forecast → Battery consequence →
  Charging planner → Future capacity engine → Risk engine → Fleet optimizer →
  Dispatcher → Learning loop

Phase 1: Returns demo data clearly labelled as DEMO.
Phase 2: Will implement full fleet pipeline.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/fleet", tags=["fleet"])


@router.get("/state")
async def get_fleet_state() -> dict:
    """Return fleet vehicle states. Phase 1: demo data."""
    return {
        "is_demo": True,
        "label": "DEMO DATA — Phase 2 implementation pending",
        "vehicles": [
            {"id": "EV-001", "soc": 78, "soh": 94, "temp": 29, "capacity": 92,
             "status": "ACTIVE", "range_km": 352},
            {"id": "EV-021", "soc": 43, "soh": 76, "temp": 34, "capacity": 62,
             "status": "PROTECT", "range_km": 164},
            {"id": "EV-009", "soc": 84, "soh": 96, "temp": 28, "capacity": 94,
             "status": "AVAILABLE", "range_km": 368},
            {"id": "EV-014", "soc": 61, "soh": 88, "temp": 31, "capacity": 81,
             "status": "CHARGING", "range_km": 246},
            {"id": "EV-006", "soc": 69, "soh": 91, "temp": 30, "capacity": 87,
             "status": "ACTIVE", "range_km": 289},
            {"id": "EV-018", "soc": 52, "soh": 83, "temp": 36, "capacity": 73,
             "status": "ACTIVE", "range_km": 201},
        ],
        "summary": {"total": 24, "active": 18, "charging": 4, "available": 2},
    }


@router.get("/demand")
async def get_fleet_demand() -> dict:
    """Return future demand forecast. Phase 1: demo data."""
    return {
        "is_demo": True,
        "label": "DEMO DATA — Replace with real demand forecast",
        "day": "TOMORROW",
        "tasks": 41,
        "change": 28,
    }
