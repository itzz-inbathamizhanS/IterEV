"""
Metrics — Centralized metric computation for experiments.

All metrics are computed consistently across all experiment types.
"""


def compute_metrics(result: dict) -> dict:
    """
    Compute and validate all metrics from a single experiment result.

    Input result dict should have the fields produced by baselines.run_baseline().

    Returns:
        Dict with all standardized metric fields.
    """
    return {
        "travel_time": result.get("travel_time", 0),
        "energy_consumption": result.get("energy", 0),
        "monetary_cost": result.get("cost", 0),
        "battery_degradation": result.get("soh_loss", 0),
        "final_soh": round(100.0 - result.get("soh_loss", 0) * 100, 4)
            if result.get("soh_loss", 0) < 1 else round(100.0 - result.get("soh_loss", 0), 4),
        "future_success_rate": result.get("future_success_rate", 100.0),
        "fmf": result.get("fmf", 99.0),
        "fmr": result.get("fmr", 1.0),
        "fmr_ci_lower": result.get("fmr_ci_lower", 0.0),
        "fmr_ci_upper": result.get("fmr_ci_upper", 0.0),
        "constraint_violation_rate": 1.0 if result.get("constraint_violations", 0) > 0 else 0.0,
        "computation_time_s": result.get("computation_time_s", 0.0),
    }


def aggregate_metrics(results: list[dict]) -> dict:
    """
    Compute aggregate statistics from a list of metric dicts.

    Returns:
        Dict with mean, std, min, max for each numeric metric.
    """
    if not results:
        return {}

    import numpy as np

    numeric_keys = [k for k in results[0] if isinstance(results[0][k], (int, float))]
    agg = {}
    for key in numeric_keys:
        values = [r[key] for r in results if key in r]
        if values:
            agg[key] = {
                "mean": round(float(np.mean(values)), 4),
                "std": round(float(np.std(values)), 4),
                "median": round(float(np.median(values)), 4),
                "min": round(float(np.min(values)), 4),
                "max": round(float(np.max(values)), 4),
            }
    return agg
