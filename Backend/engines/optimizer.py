"""
Optimizer — Research Module 5 (Decision engine, optimizer component).

Research reference:
  §18 — Mathematical Formulation:
    min J(a) = CurrentCost(a) + λ·BatteryConsequence(a) + µ·FMR(a)
    subject to: FMR(a) ≤ ε

  §14 — "Do not choose λ, µ or ε arbitrarily and then claim they are universally
         correct. The study should run sensitivity analysis."

Phase 1 implementation:
  - Deterministic: no stochastic sampling
  - All three terms normalized to [0, 1] before weighting
  - LAMBDA_BATTERY and MU_FMR from constants.py (configurable for ablation studies)
  - Returns recommended route_id and a structured score breakdown
"""

from dataclasses import dataclass
from models.schemas import RouteCandidate
from models.constants import LAMBDA_BATTERY, MU_FMR, EPSILON_FMR


@dataclass
class RouteScore:
    """Score breakdown for one route — useful for ablation analysis"""
    route_id: str
    route_name: str
    current_cost: float      # Normalized travel time + monetary cost
    battery_consequence: float  # Normalized battery degradation risk
    fmr_term: float             # Normalized future mobility risk
    total_J: float              # Total objective J(a)
    feasible: bool              # Whether FMR(a) ≤ epsilon


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Min-max normalize a value to [0, 1]. Returns 0 if range is zero."""
    r = max_val - min_val
    if r == 0:
        return 0.0
    return (value - min_val) / r


def score_routes(
    routes: list[RouteCandidate],
    lambda_battery: float = LAMBDA_BATTERY,
    mu_fmr: float = MU_FMR,
    epsilon_fmr: float = EPSILON_FMR,
    time_weight: float = 0.5,
    cost_weight: float = 0.5,
) -> list[RouteScore]:
    """
    Score all route candidates using J(a) = CurrentCost + λ·Battery + µ·FMR.

    Args:
        routes: Computed route candidates with energy, fmr, soc_after fields
        lambda_battery: Weight on battery consequence (default 0.30)
        mu_fmr: Weight on future mobility risk (default 0.50)
        epsilon_fmr: Maximum allowed FMR for feasibility (default 0.10 = 10%)
        time_weight: Sub-weight within CurrentCost for travel time
        cost_weight: Sub-weight within CurrentCost for monetary cost

    Returns:
        List of RouteScore objects, one per route.
    """
    if not routes:
        return []

    # Extract ranges for normalization
    times = [r.time for r in routes]
    costs = [r.cost for r in routes]
    socs_after = [r.after for r in routes]
    fmrs = [r.fmr for r in routes]

    min_time, max_time = min(times), max(times)
    min_cost, max_cost = min(costs), max(costs)
    min_soc, max_soc = min(socs_after), max(socs_after)
    min_fmr, max_fmr = min(fmrs), max(fmrs)

    scores = []
    for route in routes:
        # 1. Current cost: weighted combination of time and monetary cost
        t_norm = _normalize(route.time, min_time, max_time)
        c_norm = _normalize(route.cost, min_cost, max_cost)
        current_cost = time_weight * t_norm + cost_weight * c_norm

        # 2. Battery consequence: lower SOC_after = worse battery state = higher consequence
        #    We invert so that higher SOC_after → lower battery consequence
        soc_norm = _normalize(route.after, min_soc, max_soc)
        battery_consequence = 1.0 - soc_norm  # 0=best (highest SOC), 1=worst (lowest SOC)

        # 3. FMR term: normalized future mobility risk
        fmr_normalized = _normalize(route.fmr, min_fmr, max_fmr)

        # Total objective J(a)
        J = current_cost + lambda_battery * battery_consequence + mu_fmr * fmr_normalized

        # Feasibility check: FMR(a) ≤ epsilon (chance constraint)
        is_feasible = (route.fmr / 100.0) <= epsilon_fmr

        scores.append(RouteScore(
            route_id=route.id,
            route_name=route.name,
            current_cost=round(current_cost, 4),
            battery_consequence=round(battery_consequence, 4),
            fmr_term=round(fmr_normalized, 4),
            total_J=round(J, 4),
            feasible=is_feasible,
        ))

    return scores


def select_recommended(
    routes: list[RouteCandidate],
    lambda_battery: float = LAMBDA_BATTERY,
    mu_fmr: float = MU_FMR,
    epsilon_fmr: float = EPSILON_FMR,
) -> tuple[str, list[RouteScore]]:
    """
    Select the optimal route using the J(a) objective.

    Strategy:
    1. Among routes satisfying FMR ≤ epsilon, pick lowest J
    2. If no route satisfies the constraint, pick lowest J unconditionally
       (the system still recommends the best available option, with warning)

    Args:
        routes: Candidate routes
        lambda_battery: Battery weight
        mu_fmr: FMR weight
        epsilon_fmr: FMR threshold

    Returns:
        Tuple of (recommended_route_id, all_route_scores)
    """
    scores = score_routes(routes, lambda_battery, mu_fmr, epsilon_fmr)
    if not scores:
        return routes[0].id if routes else "", scores

    # Prefer feasible routes
    feasible = [s for s in scores if s.feasible]
    candidates = feasible if feasible else scores

    best = min(candidates, key=lambda s: s.total_J)
    return best.route_id, scores
