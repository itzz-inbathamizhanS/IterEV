"""
Experiment Scenarios — Defines future trip scenarios for experiments.
"""

from models.schemas import FutureTrip


def build_standard_trips(
    demand_multiplier: float = 1.0,
    planning_horizon: int = 5,
) -> list[FutureTrip]:
    """
    Build the standard set of future trips used across all experiments.

    This ensures all methods and experiments use identical trip requirements
    for fair comparison.

    Base trips:
      - Chennai (500 km, CRITICAL) — tomorrow
      - Local mobility (60 km, NORMAL) — day 3
      - Bangalore (330 km, HIGH) — day 5

    Args:
        demand_multiplier: Scales all trip distances
        planning_horizon: Determines which trips are included

    Returns:
        List of FutureTrip objects.
    """
    all_trips = [
        FutureTrip(
            id="exp_1", day="TOMORROW", origin="Coimbatore",
            destination="Chennai", distance_km=round(500.0 * demand_multiplier, 1),
            priority="CRITICAL",
        ),
        FutureTrip(
            id="exp_2", day="DAY 3", origin="Local",
            destination="Local Mobility", distance_km=round(60.0 * demand_multiplier, 1),
            priority="NORMAL",
        ),
        FutureTrip(
            id="exp_3", day="DAY 5", origin="Coimbatore",
            destination="Bangalore", distance_km=round(330.0 * demand_multiplier, 1),
            priority="HIGH",
        ),
    ]

    # Only include trips within planning horizon
    return [t for t in all_trips if _parse_day(t.day) < planning_horizon]


def _parse_day(day_str: str) -> int:
    """Parse day string to index."""
    d = day_str.strip().upper()
    if d == "TODAY":
        return 0
    if d == "TOMORROW":
        return 1
    if d.startswith("DAY"):
        try:
            return int(d.replace("DAY", "").strip()) - 1
        except ValueError:
            return 1
    return 1
