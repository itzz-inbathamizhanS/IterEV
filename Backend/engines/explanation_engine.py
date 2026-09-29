"""
Explanation Engine — Research §14 (Explanation engine component).

Research reference:
  §11 §10 — "Explanation: Generate human-readable reasons for decisions."
  §26     — "The system explains why a recommendation was selected."
  §14     — "A transparent recommendation is selected and its reasoning is retained."

The explanation should answer:
  1. WHAT was chosen
  2. WHY vs. the fastest alternative
  3. BATTERY EFFECT: what happens to SOC today
  4. FUTURE EFFECT: how it affects future feasibility
  5. RISK CHANGE: quantitative improvement in FMR

All explanations use deterministic, computed values — not fabricated text.
"""

from models.schemas import RouteCandidate


def generate_explanation(
    recommended: RouteCandidate,
    alternatives: list[RouteCandidate],
) -> dict[str, str]:
    """
    Generate structured decision explanation for the ConsumerPage DecisionTrace component.

    Matches the TraceItem format expected by the frontend:
      { label: string, value: string }

    Args:
        recommended: The optimizer-selected route
        alternatives: All candidate routes (including recommended)

    Returns:
        Dict with keys: reason_text, battery_effect, future_effect, risk_change, trade_off
    """
    fastest = min(alternatives, key=lambda r: r.time)
    most_efficient = min(alternatives, key=lambda r: r.energy)

    time_diff = recommended.time - fastest.time
    fmr_diff = round(fastest.fmr - recommended.fmr, 1)
    energy_diff = round(fastest.energy - recommended.energy, 1)

    # Primary reason text shown in the "Why this decision?" paragraph
    if recommended.constraint_relaxed:
        reason_text = (
            f"Constraint Relaxed. FMR Point Estimate is {recommended.fmr:.1f}%, "
            f"and FMR CI Upper Bound is {recommended.fmr_ci_upper:.1f}%. "
            f"Route {recommended.name} is the most balanced fallback option."
        )
    elif recommended.id == fastest.id:
        reason_text = (
            f"Route {recommended.name} is the fastest option available. "
            f"It maintains a {recommended.after:.0f}% battery state after the journey "
            f"with {recommended.feasibility:.1f}% future mobility feasibility."
        )
    elif fmr_diff > 0:
        reason_text = (
            f"Route {recommended.name} takes {time_diff} additional "
            f"{'minute' if time_diff == 1 else 'minutes'} but reduces future mobility risk "
            f"by {fmr_diff:.1f} percentage points compared to the fastest option. "
            f"This preserves a stronger battery state ({recommended.after:.0f}% vs "
            f"{fastest.after:.0f}%) for upcoming mobility requirements."
        )
    else:
        reason_text = (
            f"Route {recommended.name} balances current travel cost with "
            f"future mobility capability, achieving {recommended.feasibility:.1f}% "
            f"future feasibility."
        )

    # Battery effect
    battery_effect = f"{recommended.after:.0f}% after today"

    # Future effect
    future_effect = f"{recommended.feasibility:.1f}% feasible"

    # Risk change (vs fastest)
    if fmr_diff > 0:
        risk_change = f"−{fmr_diff:.1f} pts vs fastest"
    elif fmr_diff < 0:
        risk_change = f"+{abs(fmr_diff):.1f} pts vs fastest"
    else:
        risk_change = "Same as fastest"

    # Trade-off summary
    if time_diff > 0:
        trade_off = f"+{time_diff} min, −{fmr_diff:.1f}% risk"
    elif time_diff == 0:
        trade_off = f"Same time, −{fmr_diff:.1f}% risk"
    else:
        trade_off = f"{time_diff} min, −{fmr_diff:.1f}% risk"

    return {
        "reason_text": reason_text,
        "battery_effect": battery_effect,
        "future_effect": future_effect,
        "risk_change": risk_change,
        "trade_off": trade_off,
    }


def format_risk_label(fmr: float) -> str:
    """
    Format FMR as a risk level label.
    Matches the risk levels shown in RiskPage:
      LOW | WARNING | HIGH | CRITICAL
    """
    if fmr <= 5.0:
        return "LOW"
    elif fmr <= 12.0:
        return "WARNING"
    elif fmr <= 20.0:
        return "HIGH"
    else:
        return "CRITICAL"
